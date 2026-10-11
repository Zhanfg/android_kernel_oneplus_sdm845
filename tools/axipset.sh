#!/system/bin/sh
# AxIPSet v0.1: low-overhead policy control plane on Linux ipset.
# Interactive only; run: sh axipset.sh (without parameters).
# Does NOT inject firewall rules or change system routing.
set -u
umask 077
if [ "$(id -u 2>/dev/null)" != 0 ]; then
  echo "需要 root 权限；未修改任何规则。"
  exit 1
fi
IPSET=$(command -v ipset 2>/dev/null || true)
if [ -z "$IPSET" ]; then
  echo "找不到 ipset 用户态工具。内核功能和 ipset 命令需要分别安装。"
  exit 1
fi
name4=axynet4
name6=axynet6

ensure_sets() {
  "$IPSET" create "$name4" hash:net family inet hashsize 1024 maxelem 65536 -exist || return 1
  "$IPSET" create "$name6" hash:net family inet6 hashsize 1024 maxelem 65536 -exist || return 1
}

choose_family() {
  printf '地址或 CIDR: '
  IFS= read -r ADDRESS || return 1
  case "$ADDRESS" in
    *[!0-9a-fA-F.:/]*|'') echo "非法字符或空地址"; return 1 ;;
  esac
  case "$ADDRESS" in
    *:*) SETNAME=$name6 ;;
    *.*) SETNAME=$name4 ;;
    *) echo "无法识别 IPv4/IPv6"; return 1 ;;
  esac
  return 0
}

import_file() {
  echo "请输入仅含 IPv4/IPv6 CIDR 的文本文件绝对路径（一行一条；# 为注释）："
  IFS= read -r PATH_IN || return 1
  [ -f "$PATH_IN" ] || { echo "文件不存在"; return 1; }
  # Stage both families and atomically swap each when every line validates.
  local4=axynet4_stage
  local6=axynet6_stage
  "$IPSET" destroy "$local4" >/dev/null 2>&1 || true
  "$IPSET" destroy "$local6" >/dev/null 2>&1 || true
  "$IPSET" create "$local4" hash:net family inet hashsize 1024 maxelem 65536 || return 1
  "$IPSET" create "$local6" hash:net family inet6 hashsize 1024 maxelem 65536 || {
    "$IPSET" destroy "$local4" >/dev/null 2>&1
    return 1
  }
  failed=0
  while IFS= read -r entry || [ -n "$entry" ]; do
    case "$entry" in ''|\#*) continue ;; esac
    case "$entry" in
      *[!0-9a-fA-F.:/]*) failed=1; break ;;
      *:*) "$IPSET" add "$local6" "$entry" -exist || { failed=1; break; } ;;
      *.*) "$IPSET" add "$local4" "$entry" -exist || { failed=1; break; } ;;
      *) failed=1; break ;;
    esac
  done < "$PATH_IN"
  if [ "$failed" -eq 0 ]; then
    "$IPSET" swap "$name4" "$local4" && "$IPSET" swap "$name6" "$local6" || failed=1
  fi
  "$IPSET" destroy "$local4" >/dev/null 2>&1 || true
  "$IPSET" destroy "$local6" >/dev/null 2>&1 || true
  if [ "$failed" -eq 0 ]; then
    echo "导入完成；分别以原子 swap 更新 IPv4 和 IPv6 集合。"
  else
    echo "导入或交换失败；检查 ipset 输出。不同地址族的更新不是单次全局事务。"
  fi
}

ensure_sets || { echo "创建内核 IP 集合失败。"; exit 1; }
echo "AxIPSet: 集合已创建；未安装任何 iptables/nftables 规则。"
while :; do
  echo
  echo "1 添加CIDR  2 删除CIDR  3 查询CIDR  4 列表  5 文件导入  0 退出"
  printf '> '
  IFS= read -r action || exit 0
  case "$action" in
    1) if choose_family; then "$IPSET" add "$SETNAME" "$ADDRESS" -exist; fi ;;
    2) if choose_family; then "$IPSET" del "$SETNAME" "$ADDRESS"; fi ;;
    3) if choose_family; then "$IPSET" test "$SETNAME" "$ADDRESS"; fi ;;
    4) "$IPSET" list "$name4"; "$IPSET" list "$name6" ;;
    5) import_file ;;
    0) exit 0 ;;
    *) echo "无效菜单选项" ;;
  esac
done
