// SPDX-License-Identifier: GPL-2.0
/*
 * OP6 TrueFuel v0.2: BQ27411 independent read-only register measurements.
 * Designed for exact-match OnePlus 6 / 4.19.325 BakaSU builds only.
 * IMPORTANT: no DataFlash writes, no charging overrides, no SOC spoofing.
 * I2C register selection is a transaction pointer write, not a gauge config write.
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/power_supply.h>
#include <linux/string.h>
#include <generated/utsrelease.h>

#if !defined(CONFIG_ARM64)
#error "OP6 TrueFuel requires ARM64"
#endif

#define OP6_GAUGE_BUS 0
#define OP6_GAUGE_ADDR 0x55
#define REG_FLAGS             0x06
#define REG_RM                0x0c
#define REG_FCC               0x0e
#define REG_SOC               0x1c
#define REG_RM_UNFILTERED     0x28
#define REG_FCC_UNFILTERED    0x2c
#define REG_SOC_UNFILTERED    0x30
#define REG_DESIGN_CAPACITY   0x3c

static struct proc_dir_entry *proc;

static int get_prop(struct power_supply *psy,
                    enum power_supply_property property, int *result)
{
    union power_supply_propval value = { .intval = 0 };
    int err = power_supply_get_property(psy, property, &value);
    if (!err)
        *result = value.intval;
    return err;
}

static void show_prop(struct seq_file *s, struct power_supply *psy,
                      const char *name, enum power_supply_property property)
{
    int result;
    int err = get_prop(psy, property, &result);
    if (err)
        seq_printf(s, "%s=unavailable(%d)\n", name, err);
    else
        seq_printf(s, "%s=%d\n", name, result);
}

/* Read a standard BQ27411 16-bit register, LSB first. */
static int read_bq_word(struct i2c_adapter *adap, u8 reg, u16 *out)
{
    u8 address_byte = reg;
    u8 data[2] = { 0, 0 };
    struct i2c_msg msgs[2] = {
        { .addr = OP6_GAUGE_ADDR, .flags = 0, .len = 1,
          .buf = &address_byte },
        { .addr = OP6_GAUGE_ADDR, .flags = I2C_M_RD, .len = 2,
          .buf = data },
    };
    int ret = i2c_transfer(adap, msgs, 2);
    if (ret < 0)
        return ret;
    if (ret != 2)
        return -EIO;
    *out = (u16)data[0] | ((u16)data[1] << 8);
    return 0;
}

static void show_bq_word(struct seq_file *s, struct i2c_adapter *adap,
                         const char *name, u8 reg)
{
    u16 value;
    int err = read_bq_word(adap, reg, &value);
    if (err)
        seq_printf(s, "%s=unavailable(%d)\n", name, err);
    else
        seq_printf(s, "%s=%u\n", name, value);
}

static int op6_show(struct seq_file *s, void *ignored)
{
    struct power_supply *bms, *battery, *usb;
    struct i2c_adapter *adap;
    int state, online;
    bool safe_to_read = false;

    seq_puts(s, "OP6 TrueFuel 0.2 (NO CAPACITY OVERRIDE)\n");
    seq_puts(s, "mode=read_only; gauge_design_write=disabled\n");
    seq_puts(s, "BQ SOC (0x1c) is chip-filtered; 0x30 is chip-unfiltered.\n");
    bms = power_supply_get_by_name("bms");
    battery = power_supply_get_by_name("battery");
    usb = power_supply_get_by_name("usb");
    if (!bms || !battery || !usb) {
        seq_puts(s, "status=missing_supply; i2c_read_blocked\n");
        goto out;
    }
    if (!bms->desc || !battery->desc || !usb->desc ||
        strcmp(bms->desc->name, "bms") ||
        strcmp(battery->desc->name, "battery") ||
        strcmp(usb->desc->name, "usb")) {
        seq_puts(s, "status=unexpected_supply; i2c_read_blocked\n");
        goto out;
    }
    show_prop(s, bms, "bms.bq_soc_filtered", POWER_SUPPLY_PROP_BQ_SOC);
    show_prop(s, bms, "bms.capacity_oem", POWER_SUPPLY_PROP_CAPACITY);
    show_prop(s, bms, "bms.charge_full", POWER_SUPPLY_PROP_CHARGE_FULL);
    show_prop(s, bms, "bms.charge_full_design", POWER_SUPPLY_PROP_CHARGE_FULL_DESIGN);
    show_prop(s, bms, "bms.remaining_capacity", POWER_SUPPLY_PROP_REMAINING_CAPACITY);
    show_prop(s, bms, "bms.real_capacity_qualcomm", POWER_SUPPLY_PROP_REAL_CAPACITY);
    show_prop(s, battery, "battery.temp_decic", POWER_SUPPLY_PROP_TEMP);

    /* The original driver disables BQ I2C reads during some Dash phases.
     * Never force a register transaction when external input is present. */
    if (!get_prop(battery, POWER_SUPPLY_PROP_STATUS, &state) &&
        !get_prop(usb, POWER_SUPPLY_PROP_ONLINE, &online) &&
        state == POWER_SUPPLY_STATUS_DISCHARGING && online == 0)
        safe_to_read = true;
    if (!safe_to_read) {
        seq_puts(s, "status=charging_or_unknown; i2c_read_blocked\n");
        goto out;
    }
    adap = i2c_get_adapter(OP6_GAUGE_BUS);
    if (!adap) {
        seq_puts(s, "status=i2c_adapter_missing\n");
        goto out;
    }
    seq_puts(s, "status=discharging_i2c_register_probe\n");
    show_bq_word(s, adap, "bq.flags", REG_FLAGS);
    show_bq_word(s, adap, "bq.soc_chip_filtered_percent", REG_SOC);
    show_bq_word(s, adap, "bq.soc_chip_unfiltered_percent", REG_SOC_UNFILTERED);
    show_bq_word(s, adap, "bq.remaining_capacity_mAh", REG_RM);
    show_bq_word(s, adap, "bq.remaining_capacity_unfiltered_mAh", REG_RM_UNFILTERED);
    show_bq_word(s, adap, "bq.fcc_mAh", REG_FCC);
    show_bq_word(s, adap, "bq.fcc_unfiltered_mAh", REG_FCC_UNFILTERED);
    show_bq_word(s, adap, "bq.design_capacity_mAh", REG_DESIGN_CAPACITY);
    i2c_put_adapter(adap);
out:
    if (usb) power_supply_put(usb);
    if (battery) power_supply_put(battery);
    if (bms) power_supply_put(bms);
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
    if (strncmp(UTS_RELEASE, "4.19.325", 8) != 0)
        return -ENODEV;
    proc = proc_create("op6_truefuel", 0444, NULL, &op6_fops);
    if (!proc)
        return -ENOMEM;
    pr_info("op6_truefuel: read-only gauge register probe loaded\n");
    return 0;
}

static void __exit op6_exit(void)
{
    proc_remove(proc);
}

module_init(op6_init);
module_exit(op6_exit);
MODULE_LICENSE("GPL");
MODULE_VERSION("0.2");
MODULE_DESCRIPTION("OnePlus6 true BQ27411 filtered/unfiltered SOC read-only audit");