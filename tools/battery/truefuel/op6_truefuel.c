// SPDX-License-Identifier: GPL-2.0
/* OnePlus 6 TrueFuel: read-only TI BQ gauge telemetry for the exact 4.19 build. */
#include <linux/module.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/power_supply.h>
#include <linux/string.h>

#if !defined(CONFIG_ARM64)
#error "OnePlus 6 TrueFuel requires ARM64"
#endif

static struct proc_dir_entry *op6_entry;

static int op6_read(struct power_supply *psy,
                    enum power_supply_property prop, int *value)
{
    union power_supply_propval out = { .intval = 0 };
    int rc = power_supply_get_property(psy, prop, &out);
    if (!rc)
        *value = out.intval;
    return rc;
}

static void op6_print(struct seq_file *m, struct power_supply *psy,
                      const char *name, enum power_supply_property prop)
{
    int v, rc = op6_read(psy, prop, &v);
    if (rc)
        seq_printf(m, "%s=unavailable(%d)\n", name, rc);
    else
        seq_printf(m, "%s=%d\n", name, v);
}

static int op6_show(struct seq_file *m, void *v)
{
    struct power_supply *psy = power_supply_get_by_name("bms");
    int raw, rm, fcc;
    int a, b, c;

    seq_puts(m, "OP6 TrueFuel stage 1: read only / no writes / no UI spoof\n");
    if (!psy) {
        seq_puts(m, "status=bms_unavailable\n");
        return 0;
    }
    if (!psy->desc || strcmp(psy->desc->name, "bms")) {
        seq_puts(m, "status=wrong_power_supply\n");
        goto out;
    }
    a = op6_read(psy, POWER_SUPPLY_PROP_BQ_SOC, &raw);
    b = op6_read(psy, POWER_SUPPLY_PROP_REMAINING_CAPACITY, &rm);
    c = op6_read(psy, POWER_SUPPLY_PROP_CHARGE_FULL, &fcc);

    /* OEM BQ_SOC may return a fallback constant without a registered BQ.
     * Require consistent RM and FCC, then verify the actual gauge identity. */
    if (a || b || c || raw < 0 || raw > 100 ||
        rm < 0 || rm > 15000 || fcc < 500 || fcc > 15000)
        seq_puts(m, "status=gauge_unverified\n");
    else
        seq_puts(m, "status=gauge_values_plausible_not_calibrated\n");
    if (!a) seq_printf(m, "bq_soc_raw_percent=%d\n", raw);
    if (!b) seq_printf(m, "bq_remaining_capacity_mAh=%d\n", rm);
    if (!c) seq_printf(m, "bq_full_charge_capacity_mAh=%d\n", fcc);
    op6_print(m, psy, "bms_capacity_oem_percent", POWER_SUPPLY_PROP_CAPACITY);
    op6_print(m, psy, "bms_design_capacity_native", POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN);
    op6_print(m, psy, "bms_qualcomm_real_capacity", POWER_SUPPLY_PROP_REAL_CAPACITY);
    op6_print(m, psy, "battery_voltage_uV", POWER_SUPPLY_PROP_VOLTAGE_NOW);
    op6_print(m, psy, "battery_temperature_decic", POWER_SUPPLY_PROP_TEMP);
out:
    power_supply_put(psy);
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
    struct power_supply *psy = power_supply_get_by_name("bms");
    if (!psy)
        return -ENODEV;
    power_supply_put(psy);
    op6_entry = proc_create("op6_truefuel", 0444, NULL, &op6_fops);
    if (!op6_entry)
        return -ENOMEM;
    pr_info("op6_truefuel: read-only telemetry ready\n");
    return 0;
}

static void __exit op6_exit(void)
{
    proc_remove(op6_entry);
}

module_init(op6_init);
module_exit(op6_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("OP6 BQ raw SOC read-only telemetry");
MODULE_VERSION("0.1");
