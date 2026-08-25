# -*- coding: utf-8 -*-
"""
上传图片到 GitHub + jsDelivr 图床（单图版）
用法：
    python 上传图片.py "图片本地路径"
返回：
    jsDelivr 公开链接，可直接贴到网站 <img src="...">

说明：
    - 凭证从同目录 token.txt 读取（仅本地，已被 .gitignore 忽略，绝不提交）
    - 仓库/分支/子目录等配置在下方“配置”区，后续要改只动那里
"""
import os
import sys
import shutil
import subprocess
import urllib.parse

sys.stdout.reconfigure(line_buffering=True)  # 防止管道下失败信息被缓冲吞掉

# ===================== 配置（后续要改就改这里） =====================
仓库用户 = "shaco805"
仓库名 = "cdn-images"
分支 = "main"
本地仓库目录 = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录即仓库根
图片子目录 = ""          # 留空=放根目录；要分类可填 "images" 等
token文件名 = "token.txt"  # 同目录下放你的 PAT，必须被 .gitignore 忽略
# ===================================================================


def 读取令牌():
    路径 = os.path.join(本地仓库目录, token文件名)
    if not os.path.exists(路径):
        print(f"[错误] 没找到 {token文件名}，把你的 GitHub PAT 放进去（仅本地，勿提交到仓库）")
        sys.exit(1)
    with open(路径, "r", encoding="utf-8") as f:
        return f.read().strip().lstrip("\ufeff")  # 去 UTF-8 BOM，防破坏 URL


def 规范化文件名(原名):
    """去空格、去 Windows 非法字符，扩展名转小写，避免 jsDelivr 路径出问题"""
    名, 扩展 = os.path.splitext(原名)
    扩展 = 扩展.lower()
    非法字符 = '\\/:*?"<>|'
    for ch in 非法字符:
        名 = 名.replace(ch, "_")
    名 = 名.replace(" ", "_")
    return 名 + 扩展


def 上传(图片路径):
    if not os.path.isfile(图片路径):
        print(f"[错误] 文件不存在：{图片路径}")
        sys.exit(1)

    原文件名 = os.path.basename(图片路径)
    新文件名 = 规范化文件名(原文件名)
    目标相对 = os.path.join(图片子目录, 新文件名) if 图片子目录 else 新文件名
    目标绝对 = os.path.join(本地仓库目录, 目标相对)

    # 图片不在仓库内才复制；已在仓库内则跳过复制
    if os.path.abspath(图片路径) != os.path.abspath(目标绝对):
        shutil.copy2(图片路径, 目标绝对)
        print(f"[复制] {原文件名} -> {目标相对}")
    else:
        print(f"[跳过] 图片已在仓库内：{目标相对}")

    令牌 = 读取令牌()
    远程地址 = f"https://{仓库用户}:{令牌}@github.com/{仓库用户}/{仓库名}.git"

    # git add + commit
    try:
        subprocess.run(["git", "-C", 本地仓库目录, "add", 目标相对], check=True,
                       capture_output=True, text=True)
        subprocess.run(["git", "-C", 本地仓库目录, "commit", "-m", f"upload {新文件名}"],
                       check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "")
        if "author identity" in msg or "user.name" in msg:
            print("[失败] git 未配置身份，请先执行：")
            print('  git config --global user.name "你的名"')
            print('  git config --global user.email "你的邮箱"')
        else:
            print(f"[失败] git add/commit 出错：{msg[:300]}")
        sys.exit(1)

    # git push：禁用 credential helper（防其抢走 URL 内嵌 token 导致静默失败），禁止交互提示
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(
        ["git", "-c", "credential.helper=", "-C", 本地仓库目录, "push", 远程地址, 分支],
        capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print("[失败] git push 出错，排查：")
        print("  1) token.txt 里的 PAT 是否有效（之前泄露的那串必须已 Revoke，用新生成的）")
        print("  2) 网络能否直连 GitHub（国内不稳可开代理或 SSH 走 443）")
        print("  3) 仓库名/分支是否正确")
        print("  （如需要更多线索，终端手动跑 git push 看详细报错）")
        sys.exit(1)

    链接 = f"https://cdn.jsdelivr.net/gh/{仓库用户}/{仓库名}@{分支}/{urllib.parse.quote(目标相对, safe='/')}"
    print("\n✅ 上传成功！jsDelivr 链接：")
    print(链接)
    return 链接


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('用法：python 上传图片.py "图片路径"')
        sys.exit(1)
    上传(sys.argv[1])
