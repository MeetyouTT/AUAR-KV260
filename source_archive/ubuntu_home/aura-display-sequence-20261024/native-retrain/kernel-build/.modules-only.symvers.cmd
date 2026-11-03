cmd_modules-only.symvers := sed 's/\.ko$$/\.o/' modules.order | scripts/mod/modpost   -E -o modules-only.symvers -i vmlinux.symvers   -T -
