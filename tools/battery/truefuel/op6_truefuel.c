// SPDX-License-Identifier: GPL-2.0
/*
 * OP6 TrueFuel 0.3: low-overhead, fail-closed telemetry bridge.
 *
 * Direct I2C was removed: the proprietary BQ driver controls the gauge
 * during Dash and DataFlash updates. Any unfiltered measurements must go
 * through the built-in bq27541 driver, which owns battery_mutex.
 *
 * IMPORTANT: no DataFlash writes, no charge-control writes, no SOC spoofing.
 */
#include <linux/module.h>
#include <linux/init.h>
#include <linux/errno.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/power_supply.h>
#include <linux/string.h>
#include <generated/utsrelease.h>

#if !defined(CONFIG_ARM64)
#error "OP6 TrueFuel is restricted to ARM64"
#endif

static struct proc_dir_entry *truefuel_proc;

static void op6_prop(struct seq_file *m, struct power_supply *psy,
		     const char *key, enum power_supply_property psp)
{
	union power_supply_propval v = { .intval = 0 };
	int ret;

	ret = power_supply_get_property(psy, psp, &v);
	if (ret)
		seq_printf(m, "%s=unavailable(%d)\n", key, ret);
	else
		seq_printf(m, "%s=%d\n", key, v.intval);
}

static int op6_show(struct seq_file *m, void *unused)
{
	struct power_supply *bms = power_supply_get_by_name("bms");
	struct power_supply *battery = power_supply_get_by_name("battery");

	seq_puts(m, "OP6 TrueFuel 0.3 - NO gauge I2C / NO capacity override\n");
	seq_puts(m, "hardware_soc_path=/sys/bus/i2c/devices/0-0055/op6_truefuel_hw\n");
	if (!bms || !battery || !bms->desc || !battery->desc ||
	    strcmp(bms->desc->name, "bms") ||
	    strcmp(battery->desc->name, "battery")) {
		seq_puts(m, "status=required_power_supply_missing\n");
		goto out;
	}
	seq_puts(m, "status=read_only_existing_power_supply\n");
	op6_prop(m, bms, "bms.bq_soc_chip_filtered_pct",
		 POWER_SUPPLY_PROP_BQ_SOC);
	op6_prop(m, bms, "bms.capacity_oem_smoothed_pct",
		 POWER_SUPPLY_PROP_CAPACITY);
	op6_prop(m, bms, "bms.real_capacity_qualcomm_pct",
		 POWER_SUPPLY_PROP_REAL_CAPACITY);
	op6_prop(m, bms, "bms.charge_full_uAh",
		 POWER_SUPPLY_PROP_CHARGE_FULL);
	op6_prop(m, bms, "bms.charge_full_design_uAh",
		 POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN);
	/* OEM remaining_capacity is mAh, unlike charge_full's uAh. */
	op6_prop(m, bms, "bms.remaining_capacity_mAh",
		 POWER_SUPPLY_PROP_REMAINING_CAPACITY);
	op6_prop(m, battery, "battery.capacity_pct",
		 POWER_SUPPLY_PROP_CAPACITY);
	op6_prop(m, battery, "battery.temp_decic",
		 POWER_SUPPLY_PROP_TEMP);
	op6_prop(m, battery, "battery.status",
		 POWER_SUPPLY_PROP_STATUS);
out:
	if (battery)
		power_supply_put(battery);
	if (bms)
		power_supply_put(bms);
	return 0;
}

static int op6_open(struct inode *inode, struct file *file)
{
	return single_open(file, op6_show, NULL);
}

static const struct file_operations op6_fops = {
	.owner = THIS_MODULE,
	.open = op6_open,
	.read = seq_read,
	.llseek = seq_lseek,
	.release = single_release,
};

static int __init op6_init(void)
{
	if (strncmp(UTS_RELEASE, "4.19.325", 8))
		return -ENODEV;
	truefuel_proc = proc_create("op6_truefuel", 0444, NULL, &op6_fops);
	if (!truefuel_proc)
		return -ENOMEM;
	pr_info("op6_truefuel: readonly PSY bridge ready\n");
	return 0;
}

static void __exit op6_exit(void)
{
	proc_remove(truefuel_proc);
}

module_init(op6_init);
module_exit(op6_exit);
MODULE_LICENSE("GPL");
MODULE_VERSION("0.3");
MODULE_DESCRIPTION("OnePlus6 TrueFuel power_supply bridge - read-only");
