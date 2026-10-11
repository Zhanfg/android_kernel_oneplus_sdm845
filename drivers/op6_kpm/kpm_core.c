// SPDX-License-Identifier: GPL-2.0-only
/* OP6 native KPM ABI stage 2A: fail-closed. NO KPM code execution. */
#include <linux/capability.h>
#include <linux/elf.h>
#include <linux/errno.h>
#include <linux/file.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/op6_kpm.h>
#include <linux/string.h>
#include <linux/uaccess.h>
#include <linux/vmalloc.h>

static bool valid_name(const char *s)
{
	size_t i, n = strnlen(s, 32);
	if (!n || n >= 32)
		return false;
	for (i = 0; i < n; ++i) {
		char c = s[i];
		if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
		      (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.'))
			return false;
	}
	return true;
}
static int parse_tag(char *dst, size_t cap, const char *name,
		     const char *buf, size_t len)
{
	size_t keylen = strlen(name), val_len;
	if (len <= keylen + 1 || memcmp(name, buf, keylen) ||
	    buf[keylen] != '=')
		return 0;
	val_len = len - keylen - 1;
	if (val_len >= cap || dst[0])
		return -ENOEXEC;
	memcpy(dst, buf + keylen + 1, val_len);
	dst[val_len] = 0;
	return 0;
}
static int parse_metadata(struct op6_kpm_inspect *req,
			  const char *data, size_t len)
{
	size_t at = 0;
	while (at < len) {
		size_t n = strnlen(data + at, len - at);
		if (n == len - at)
			return -ENOEXEC;
		if (parse_tag(req->name, sizeof(req->name), "name",
			      data + at, n) ||
		    parse_tag(req->version, sizeof(req->version), "version",
			      data + at, n) ||
		    parse_tag(req->license, sizeof(req->license), "license",
			      data + at, n) ||
		    parse_tag(req->author, sizeof(req->author), "author",
			      data + at, n))
			return -ENOEXEC;
		at += n + 1;
	}
	return valid_name(req->name) ? 0 : -ENOEXEC;
}
static int inspect_elf(const void *data, size_t len,
		       struct op6_kpm_inspect *req)
{
	const Elf64_Ehdr *h = data;
	const Elf64_Shdr *shdr, *ns;
	const char *names, *info = NULL;
	size_t nameslen, infolen = 0, i;
	bool has_init = false;

	if (len < sizeof(*h) || memcmp(h->e_ident, ELFMAG, SELFMAG) ||
	    h->e_ident[EI_CLASS] != ELFCLASS64 ||
	    h->e_ident[EI_DATA] != ELFDATA2LSB ||
	    h->e_ident[EI_VERSION] != EV_CURRENT ||
	    h->e_type != ET_REL || h->e_machine != EM_AARCH64 ||
	    h->e_version != EV_CURRENT || h->e_entry ||
	    h->e_ehsize != sizeof(*h) || h->e_phnum || h->e_phoff ||
	    h->e_shentsize != sizeof(Elf64_Shdr) ||
	    h->e_shnum < 2 || h->e_shnum > 512 ||
	    !h->e_shstrndx || h->e_shstrndx >= h->e_shnum)
		return -ENOEXEC;
	if (h->e_shoff > len ||
	    h->e_shnum > (len - h->e_shoff) / sizeof(Elf64_Shdr))
		return -ENOEXEC;
	shdr = (const Elf64_Shdr *)((const char *)data + h->e_shoff);
	ns = &shdr[h->e_shstrndx];
	if (ns->sh_type != SHT_STRTAB || ns->sh_offset > len ||
	    ns->sh_size > len - ns->sh_offset)
		return -ENOEXEC;
	names = (const char *)data + ns->sh_offset;
	nameslen = ns->sh_size;
	for (i = 1; i < h->e_shnum; ++i) {
		const Elf64_Shdr *s = &shdr[i];
		const char *name;
		size_t remain;
		if (s->sh_type != SHT_NOBITS &&
		    (s->sh_offset > len || s->sh_size > len - s->sh_offset))
			return -ENOEXEC;
		if (s->sh_addralign &&
		    (s->sh_addralign & (s->sh_addralign - 1)))
			return -ENOEXEC;
		if (s->sh_name >= nameslen)
			return -ENOEXEC;
		name = names + s->sh_name;
		remain = nameslen - s->sh_name;
		if (strnlen(name, remain) == remain)
			return -ENOEXEC;
		if (!strcmp(name, ".kpm.info")) {
			if (info || !s->sh_size || !(s->sh_flags & SHF_ALLOC) ||
			    s->sh_type == SHT_NOBITS)
				return -ENOEXEC;
			info = (const char *)data + s->sh_offset;
			infolen = s->sh_size;
		} else if (!strcmp(name, ".kpm.init")) {
			if (has_init || s->sh_type == SHT_NOBITS ||
			    !(s->sh_flags & SHF_ALLOC) ||
			    s->sh_size < 8 || s->sh_size % 8)
				return -ENOEXEC;
			has_init = true;
		}
		if (s->sh_type == SHT_DYNAMIC)
			return -ENOEXEC;
	}
	if (!info || !has_init)
		return -ENOEXEC;
	return parse_metadata(req, info, infolen);
}
static int inspect_file(struct op6_kpm_inspect *req)
{
	struct file *f;
	void *data;
	loff_t len, pos = 0;
	ssize_t n;
	size_t at = 0;
	int rc = -EINVAL;
	if (req->fd < 0 || req->flags || req->reserved)
		return rc;
	f = fget(req->fd);
	if (!f)
		return -EBADF;
	if (!S_ISREG(file_inode(f)->i_mode))
		goto out_file;
	len = i_size_read(file_inode(f));
	if (len < sizeof(Elf64_Ehdr) || len > OP6_KPM_MAX_FILE) {
		rc = -EFBIG;
		goto out_file;
	}
	data = vmalloc(len);
	if (!data) {
		rc = -ENOMEM;
		goto out_file;
	}
	while (at < (size_t)len) {
		n = kernel_read(f, (char *)data + at, len - at, &pos);
		if (n <= 0) {
			rc = n < 0 ? n : -EIO;
			goto out_data;
		}
		at += n;
	}
	memset(req->name, 0, sizeof(req->name));
	memset(req->version, 0, sizeof(req->version));
	memset(req->license, 0, sizeof(req->license));
	memset(req->author, 0, sizeof(req->author));
	rc = inspect_elf(data, len, req);
	if (!rc)
		req->size = len;
out_data:
	vfree(data);
out_file:
	fput(f);
	return rc;
}
static long op6_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	void __user *p = (void __user *)arg;
	struct op6_kpm_abi abi = {
		.version = OP6_KPM_ABI_VERSION,
		.caps = OP6_KPM_CAP_INSPECT,
		.max_file = OP6_KPM_MAX_FILE,
		.active_modules = 0,
	};
	struct op6_kpm_inspect req;
	int rc;

	/* Permission only after kernel LSM/device-node access checks. */
	if (!capable(CAP_SYS_MODULE))
		return -EPERM;
	switch (cmd) {
	case OP6_KPM_IOCTL_GET_ABI:
		return copy_to_user(p, &abi, sizeof(abi)) ? -EFAULT : 0;
	case OP6_KPM_IOCTL_INSPECT:
		if (copy_from_user(&req, p, sizeof(req)))
			return -EFAULT;
		rc = inspect_file(&req);
		if (rc)
			return rc;
		return copy_to_user(p, &req, sizeof(req)) ? -EFAULT : 0;
	default:
		return -ENOTTY; /* LOAD/UNLOAD/CONTROL not implemented */
	}
}
static const struct file_operations op6_fops = {
	.owner = THIS_MODULE,
	.unlocked_ioctl = op6_ioctl,
#ifdef CONFIG_COMPAT
	.compat_ioctl = op6_ioctl,
#endif
	.llseek = no_llseek,
};
static struct miscdevice op6_device = {
	.minor = MISC_DYNAMIC_MINOR,
	.name = "op6-kpm",
	.mode = 0600,
	.fops = &op6_fops,
};
static int __init op6_kpm_init(void)
{
	int rc = misc_register(&op6_device);
	if (!rc)
		pr_info("op6-kpm ABI v1: metadata inspection ONLY; loader disabled\n");
	return rc;
}
device_initcall(op6_kpm_init);
MODULE_LICENSE("GPL");
