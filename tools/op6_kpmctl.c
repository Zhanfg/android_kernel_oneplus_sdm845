/* SPDX-License-Identifier: GPL-2.0-only */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "../include/uapi/linux/op6_kpm.h"
int main(int argc, char **argv)
{
	struct op6_kpm_abi abi = {0};
	struct op6_kpm_inspect info = {0};
	int dev, fd = -1, rc = 2;
	if (argc < 2 || (strcmp(argv[1], "status") &&
	    (strcmp(argv[1], "inspect") || argc != 3))) {
		fprintf(stderr, "Usage: %s status | inspect FILE\n", argv[0]);
		return rc;
	}
	dev = open("/dev/op6-kpm", O_RDONLY | O_CLOEXEC);
	if (dev < 0) {
		perror("open /dev/op6-kpm");
		return rc;
	}
	if (ioctl(dev, OP6_KPM_IOCTL_GET_ABI, &abi) < 0) {
		perror("KPM_GET_ABI");
		goto end;
	}
	if (abi.version != OP6_KPM_ABI_VERSION) {
		fprintf(stderr, "unsupported KPM ABI %u\n", abi.version);
		goto end;
	}
	if (!strcmp(argv[1], "status")) {
		printf("abi=%u\ncaps=0x%x\nmax_file=%u\nactive_modules=%u\nloader=no\n",
		       abi.version, abi.caps, abi.max_file, abi.active_modules);
		rc = 0;
		goto end;
	}
	if (!(abi.caps & OP6_KPM_CAP_INSPECT)) {
		fprintf(stderr, "KPM ELF inspection not supported\n");
		goto end;
	}
	fd = open(argv[2], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
	if (fd < 0) {
		perror("open KPM file");
		goto end;
	}
	info.fd = fd;
	if (ioctl(dev, OP6_KPM_IOCTL_INSPECT, &info) < 0) {
		perror("KPM_INSPECT");
		goto end;
	}
	printf("name=%s\nversion=%s\nlicense=%s\nauthor=%s\nsize=%u\nactive=no\n",
	       info.name, info.version, info.license, info.author, info.size);
	rc = 0;
end:
	if (fd >= 0)
		close(fd);
	close(dev);
	return rc;
}
