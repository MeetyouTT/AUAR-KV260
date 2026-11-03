// SPDX-License-Identifier: GPL-2.0
/* Runtime candidate, not a boot component. Diagnostic-only is the default.
 * No hard-coded kernel address, private DP structure layout, GPIO or flash.
 * Calls the already running driver's verified training function only after
 * an explicit enable_action=1 load and a separate single trigger=1 write.
 */
#include <linux/atomic.h>
#include <linux/completion.h>
#include <linux/device.h>
#include <linux/interrupt.h>
#include <linux/kprobes.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/notifier.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/ptrace.h>
#include <linux/string.h>
#include <linux/utsname.h>
#include <drm/drm_device.h>
#include <drm/drm_connector.h>
#include <drm/drm_crtc.h>
#include <drm/drm_drv.h>
#include <drm/drm_modeset_lock.h>

static bool enable_action;
module_param(enable_action, bool, 0444);
MODULE_PARM_DESC(enable_action, "False by default; true still needs a one-shot trigger");
static unsigned int capture_timeout_ms = 5000;
module_param(capture_timeout_ms, uint, 0444);

static struct device *display_device;
static struct drm_device *display_drm;
static void *display_dp;
static void (*native_train)(void *);
static int display_irq;
static DECLARE_COMPLETION(dp_seen);
static DECLARE_COMPLETION(drm_seen);
static atomic_t dp_captured = ATOMIC_INIT(0);
static atomic_t drm_captured = ATOMIC_INIT(0);
static atomic_t fired = ATOMIC_INIT(0);
static DEFINE_MUTEX(action_lock);
static bool ready;
static bool action_returned;
static int action_error;
static atomic_t invalidated = ATOMIC_INIT(0);
static struct device_driver *captured_driver;
static void *captured_drvdata;

/* Device references do not prevent unbind. Invalidate before the existing
 * driver's state can be freed, and never re-arm after a later rebind.
 * The callback does not take action_lock: unbind already holds device_lock.
 */
static int display_bus_event(struct notifier_block *notifier,
                             unsigned long event, void *data)
{
    (void)notifier;
    if (data == display_device &&
        (event == BUS_NOTIFY_UNBIND_DRIVER || event == BUS_NOTIFY_DEL_DEVICE)) {
        atomic_set(&invalidated, 1);
        WRITE_ONCE(ready, false);
    }
    return NOTIFY_DONE;
}

static struct notifier_block display_notifier = {
    .notifier_call = display_bus_event,
};

static int capture_irq(struct kprobe *probe, struct pt_regs *regs)
{
    unsigned long irq = regs_get_kernel_argument(regs, 0);
    void *dp = (void *)regs_get_kernel_argument(regs, 1);

    (void)probe;
    if ((int)irq != display_irq || !dp)
        return 0;
    if (atomic_cmpxchg(&dp_captured, 0, 1) == 0) {
        WRITE_ONCE(display_dp, dp);
        complete(&dp_seen);
    }
    return 0;
}

static int capture_drm(struct kprobe *probe, struct pt_regs *regs)
{
    struct drm_device *drm = (void *)regs_get_kernel_argument(regs, 0);

    (void)probe;
    /* Public DRM argument and public dev field; reject the separate DPU DRM. */
    if (!drm || READ_ONCE(drm->dev) != display_device)
        return 0;
    if (atomic_cmpxchg(&drm_captured, 0, 1) == 0) {
        drm_dev_get(drm);
        WRITE_ONCE(display_drm, drm);
        complete(&drm_seen);
    }
    return 0;
}

static struct kprobe irq_probe = {
    .symbol_name = "zynqmp_dp_irq_handler",
    .pre_handler = capture_irq,
};
static struct kprobe drm_probe = {
    .symbol_name = "drm_mode_getresources",
    .pre_handler = capture_drm,
};

static int status_get(char *buffer, const struct kernel_param *parameter)
{
    (void)parameter;
    return scnprintf(buffer, PAGE_SIZE,
        "ready=%u enable_action=%u dp_captured=%d drm_captured=%d "
        "triggered=%d action_returned=%u action_error=%d invalidated=%d\n",
        READ_ONCE(ready), enable_action, atomic_read(&dp_captured),
        atomic_read(&drm_captured), atomic_read(&fired),
        READ_ONCE(action_returned), READ_ONCE(action_error), atomic_read(&invalidated));
}

/* All fields inspected here belong to public DRM structures and are read
 * under all modeset locks. Reject dormant/disconnected/multiple DP outputs.
 */
static bool single_active_dp_output(void)
{
    struct drm_connector *connector;
    unsigned int found = 0;

    list_for_each_entry(connector, &display_drm->mode_config.connector_list, head) {
        if (connector->connector_type != DRM_MODE_CONNECTOR_DisplayPort)
            continue;
        found++;
        if (connector->status != connector_status_connected ||
            !connector->state || !connector->state->crtc ||
            !connector->state->crtc->state || !connector->state->crtc->state->active)
            return false;
    }
    return found == 1;
}

static int trigger_set(const char *text, const struct kernel_param *parameter)
{
    unsigned int value;
    int error;

    (void)parameter;
    error = kstrtouint(text, 0, &value);
    if (error || value != 1)
        return -EINVAL;
    if (!enable_action || !READ_ONCE(ready))
        return -EPERM;
    if (!try_module_get(THIS_MODULE))
        return -EBUSY;
    mutex_lock(&action_lock);
    if (atomic_cmpxchg(&fired, 0, 1) != 0) {
        error = -EALREADY;
        goto unlock;
    }
    device_lock(display_device);
    if (atomic_read(&invalidated) || !READ_ONCE(ready) ||
        display_device->driver != captured_driver ||
        dev_get_drvdata(display_device) != captured_drvdata ||
        !display_dp || !display_drm || !native_train) {
        error = -ENODEV;
        goto device_unlock;
    }
    error = pm_runtime_resume_and_get(display_device);
    if (error < 0)
        goto device_unlock;
    /* Serialize with normal DRM modesets and the threaded DP IRQ path. */
    drm_modeset_lock_all(display_drm);
    if (!single_active_dp_output()) {
        error = -ENOLINK;
        goto modeset_unlock;
    }
    disable_irq(display_irq);
    native_train(display_dp);
    enable_irq(display_irq);
    WRITE_ONCE(action_returned, true);
    error = 0;
modeset_unlock:
    drm_modeset_unlock_all(display_drm);
    pm_runtime_put(display_device);
device_unlock:
    device_unlock(display_device);
    WRITE_ONCE(action_error, error);
unlock:
    mutex_unlock(&action_lock);
    module_put(THIS_MODULE);
    return error;
}

static const struct kernel_param_ops status_operations = {
    .get = status_get,
};
static const struct kernel_param_ops trigger_operations = {
    .set = trigger_set,
};
module_param_cb(status, &status_operations, NULL, 0444);
module_param_cb(trigger, &trigger_operations, NULL, 0200);

static int __init candidate_init(void)
{
    struct kprobe lookup = { .symbol_name = "zynqmp_dp_train_loop" };
    struct platform_device *platform;
    int error;
    bool irq_registered = false, drm_registered = false, notifier_registered = false;

    if (strcmp(init_uts_ns.name.release, "5.15.36-xilinx-v2022.2") ||
        !capture_timeout_ms || capture_timeout_ms > 5000)
        return -EINVAL;
    display_device = bus_find_device_by_name(&platform_bus_type, NULL,
                                             "fd4a0000.display");
    if (!display_device)
        return -ENODEV;
    error = bus_register_notifier(&platform_bus_type, &display_notifier);
    if (error)
        goto failure;
    notifier_registered = true;
    device_lock(display_device);
    captured_driver = display_device->driver;
    captured_drvdata = dev_get_drvdata(display_device);
    device_unlock(display_device);
    if (!captured_driver || !captured_drvdata) {
        error = -ENODEV;
        goto failure;
    }
    platform = to_platform_device(display_device);
    display_irq = platform_get_irq(platform, 0);
    if (display_irq < 0) {
        error = display_irq;
        goto failure;
    }
    error = register_kprobe(&lookup);
    if (error)
        goto failure;
    native_train = (void *)lookup.addr;
    unregister_kprobe(&lookup);
    error = register_kprobe(&irq_probe);
    if (error)
        goto failure;
    irq_registered = true;
    error = register_kprobe(&drm_probe);
    if (error)
        goto failure;
    drm_registered = true;
    /* A concurrent read-only modetest GETRESOURCES supplies the public DRM
     * argument. A normal display IRQ supplies the opaque DP driver argument.
     */
    if (!wait_for_completion_timeout(&dp_seen,
            msecs_to_jiffies(capture_timeout_ms)) ||
        !wait_for_completion_timeout(&drm_seen,
            msecs_to_jiffies(capture_timeout_ms))) {
        error = -ETIMEDOUT;
        goto failure;
    }
    unregister_kprobe(&drm_probe);
    unregister_kprobe(&irq_probe);
    drm_registered = false;
    irq_registered = false;
    device_lock(display_device);
    if (atomic_read(&invalidated) || display_device->driver != captured_driver ||
        dev_get_drvdata(display_device) != captured_drvdata) {
        device_unlock(display_device);
        error = -ENODEV;
        goto failure;
    }
    WRITE_ONCE(ready, true);
    device_unlock(display_device);
    pr_info("aura DP candidate ready; enable_action=%u; no action on load\n", enable_action);
    return 0;
failure:
    pr_info("aura DP candidate refused: error=%d dp=%d drm=%d invalidated=%d\n",
            error, atomic_read(&dp_captured), atomic_read(&drm_captured),
            atomic_read(&invalidated));
    if (drm_registered)
        unregister_kprobe(&drm_probe);
    if (irq_registered)
        unregister_kprobe(&irq_probe);
    if (notifier_registered)
        bus_unregister_notifier(&platform_bus_type, &display_notifier);
    if (display_drm) {
        drm_dev_put(display_drm);
        display_drm = NULL;
    }
    put_device(display_device);
    display_device = NULL;
    return error;
}

static void __exit candidate_exit(void)
{
    mutex_lock(&action_lock);
    WRITE_ONCE(ready, false);
    bus_unregister_notifier(&platform_bus_type, &display_notifier);
    drm_dev_put(display_drm);
    put_device(display_device);
    mutex_unlock(&action_lock);
}

module_init(candidate_init);
module_exit(candidate_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("One-shot candidate for the existing PS DP driver's training path; default diagnostic only");
