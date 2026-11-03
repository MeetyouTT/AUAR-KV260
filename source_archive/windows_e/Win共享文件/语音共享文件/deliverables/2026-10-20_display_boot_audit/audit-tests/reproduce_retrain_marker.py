"""Inject OFF failure into the current launcher's mocked display commands."""
import hashlib,json,unittest
from pathlib import Path
import launcher
from test_display_startup import ColdStartupTests


class MarkerAudit(ColdStartupTests):
    def run_command(self,args,env):
        value=super().run_command(args,env)
        if args==['xrandr','--output','DP-1','--off']:
            raise RuntimeError('fixture: output OFF command failed')
        return value

    def test_failed_off_still_reported_as_retrained(self):
        setup=launcher.configure_display(self.config,{})
        marker=json.loads(Path(self.config['display_recovery_marker']).read_text())
        self.assertEqual(self.off_count(),1)
        self.assertTrue(setup['startup_output_retrained'])
        self.assertTrue(marker['software_modeset_verified'])
        self.assertFalse(setup['physical_panel_verified'])
        result=dict(status='OFFLINE_FALSE_RETRAIN_SUCCESS_REPRODUCED',
                    all_display_commands_mocked=True,board_accessed=False,
                    off_successful=False,off_attempts=self.off_count(),
                    reported_startup_output_retrained=setup['startup_output_retrained'],
                    reported_software_modeset_verified=marker['software_modeset_verified'],
                    installed_occurrence_proven=False,
                    launcher_sha256=hashlib.sha256(Path(launcher.__file__).read_bytes()).hexdigest())
        Path('marker-reproduction.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))


if __name__=='__main__':
    suite=unittest.TestSuite([MarkerAudit('test_failed_off_still_reported_as_retrained')])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
