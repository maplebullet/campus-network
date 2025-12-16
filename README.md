# 校园网认证离线部署完全指南

这份文档将手把手教你如何将网页打包成 Docker 镜像，并在 Windows 电脑或 OpenWrt 路由器上离线运行。同时包含了自动登录脚本的使用方法。

---

## 📋 目录
1. [环境准备与 Docker 安装](#1-环境准备与-docker-安装)
2. [解决网络问题：配置镜像加速](#2-解决网络问题配置镜像加速)
3. [构建与测试（Windows 端）](#3-构建与测试windows-端)
4. [打包导出离线安装包](#4-打包导出离线安装包)
5. [在 OpenWrt 路由器上部署](#5-在-openwrt-路由器上部署)
6. [进阶：使用 Python 脚本自动登录](#6-进阶使用-python-脚本自动登录)

---

## 1. 环境准备与 Docker 安装

### 第一步：准备文件
确保你的文件夹（例如 `G:\web`）里包含以下文件：
- `1.html` (你的网页文件)
- `Dockerfile` (构建规则)
- `docker-compose.yml` (启动规则)
- `login.py` (自动登录脚本)

### 第二步：安装 Docker Desktop
1. 前往 [Docker 官网](https://www.docker.com/products/docker-desktop/) 下载 **Docker Desktop for Windows**。
2. 双击安装包，一路点击 "Next" 安装。
3. 安装完成后重启电脑。
4. 启动 Docker Desktop，等待左下角图标变绿。

---

## 2. 解决网络问题：配置镜像加速

国内网络直接下载镜像通常会失败，必须配置加速器。

1. 打开 Docker Desktop 界面。
2. 点击右上角的 **齿轮图标 (Settings)**。
3. 选择左侧的 **Docker Engine**。
4. 在右侧的文本框中，**完全替换**或**添加**以下内容：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://huecker.io",
    "https://dockerhub.timeweb.cloud",
    "https://noohub.ru"
  ]
}
```
5. 点击右下角的 **Apply & restart**。

---

## 3. 构建与测试（Windows 端）

在 VS Code 或 PowerShell 中打开你的项目文件夹（`G:\web`）。

### 运行命令
```powershell
docker-compose up -d --build
```

### 验证
打开浏览器访问：[http://localhost:8080](http://localhost:8080)
如果能看到网页，说明构建成功！

---

## 4. 打包导出离线安装包

根据你的路由器类型，选择对应的打包命令。

### x86 架构（软路由、Intel/AMD CPU）
大多数软路由使用此架构。
```powershell
# 1. 确保镜像已构建
docker build -t web-web:latest .

# 2. 导出为 tar 包
docker save -o web-site-x86.tar web-web:latest
```

## 5. 在 OpenWrt 路由器上部署

### 第一步：上传文件
使用 **WinSCP** 工具：
1. 协议选 SCP，输入路由器 IP（如 `192.168.5.1`）、账号（root）、密码。
2. 将生成的 `.tar` 文件拖入路由器的 `/tmp` 目录。
3. 将 `login.py` 拖入路由器的 `/root` 目录。

### 第二步：导入镜像
登录路由器的 SSH（终端），执行：

```bash
#  x86
docker load -i /tmp/web-site-x86.tar

```

### 第三步：运行容器
为了避免端口冲突，建议使用 `8090` 端口。

```bash
# x86 运行命令
docker run -d --name my-web-site --restart always -p 8090:80 web-web:latest



现在，访问 `http://路由器IP:8090` 即可看到网页。

---

## 6. 进阶：使用 Python 脚本自动登录

如果你不想手动点网页，可以使用脚本在后台自动登录。

### 第一步：安装依赖
OpenWrt 的 Python 环境默认缺失很多库，需要手动补全。在 SSH 中执行：

```bash
opkg update
opkg install python3-light python3-codecs python3-openssl python3-urllib
```

### 第二步：运行脚本
```bash
# 语法：python3 脚本路径 学号 密码
python3 /root/login.py 123456 123456
```

如果显示 `[+] 登录成功！`，则说明一切正常。

### 第三步：设置开机自动登录
编辑 `/etc/rc.local` 文件，在 `exit 0` 之前添加：
```bash
sleep 30  # 等待网络初始化
python3 /root/login.py 123456 123456
```
