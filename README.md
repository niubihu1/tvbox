<div align="center">

<img src="./logo.png" alt="牛虎 TVBox" width="96" />

# 🐯 牛虎 ┃ TVBox 全功能精选订阅

**免登秒播置顶 · 148 站全网聚搜 · 脚本双轨自托管 · 每日两次自动测活剔死链**

[![Star 收藏](https://img.shields.io/github/stars/niubihu1/tvbox?style=flat-square&color=gold&label=Star%20%E6%94%B6%E8%97%8F)](https://github.com/niubihu1/tvbox/stargazers)
[![最近更新](https://img.shields.io/github/last-commit/niubihu1/tvbox?style=flat-square&color=blue&label=%E6%9C%80%E8%BF%91%E6%9B%B4%E6%96%B0)](https://github.com/niubihu1/tvbox/commits/main)
[![接口状态](https://img.shields.io/badge/接口状态-高速存活-brightgreen?style=flat-square)](https://github.com/niubihu1/tvbox)
[![精选站源](https://img.shields.io/badge/精选站源-195%20站-blue?style=flat-square)](./1.json)
[![聚搜支持](https://img.shields.io/badge/聚搜换源-143%20站-ff69b4?style=flat-square)](./1.json)
[![公网直播](https://img.shields.io/badge/直播线路-14%20路%20(9公网)-orange?style=flat-square)](./live.txt)
[![安全门禁](https://img.shields.io/badge/Gatekeeper-10%20项全过-red?style=flat-square)](./1.json)

[🚀 一键订阅](#-订阅地址) · [✨ 核心优势](#-为什么选择牛虎) · [📊 接口构成](#-接口构成) · [📥 客户端下载](#-客户端下载) · [📖 三步导入](#-三步导入) · [💡 常见问题](#-常见问题)

</div>

<p align="center">
  全网汇聚 <b>2,000+</b> 候选接口，经并发切片测活与 <b>10 项 Gatekeeper 硬门禁</b> 自动剔除死链与失效源，每天早晚自动巡检更新。<br>
  站源与底座致谢：感谢 <b>肥猫、饭太硬、摸鱼、王二小、EasyTV、俊于、道长、心魔</b> 等一线大仓作者的持续维护与无私分享。
</p>

---

## 🚀 订阅地址

> [!TIP]
> **99% 的用户只需复制下面这一条主力单仓接口**：点击代码框右上角 **复制图标**，粘贴到播放器 **「设置 ➔ 配置地址」** 确定即可（点播、4K 网盘、电视直播一站全包）。

```text
https://gh-proxy.org/https://raw.githubusercontent.com/niubihu1/tvbox/main/1.json
```

### 🧩 扩展接口（按需选用）

* **📦 精选多仓聚合**（[`tv8.json`](./tv8.json) · 16 线 · 适用 影视仓 TV / 月光宝盒 / FongMi 多仓）
  ```text
  https://gh-proxy.org/https://raw.githubusercontent.com/niubihu1/tvbox/main/tv8.json
  ```

* **🪜 主流大仓天梯**（[`自用仓库.txt`](./自用仓库.txt) · 22 线 · 一键切换肥猫、饭太硬、摸鱼儿等一线大仓）
  ```text
  https://gh-proxy.org/https://raw.githubusercontent.com/niubihu1/tvbox/main/自用仓库.txt
  ```

* **📺 独立电视直播**（[`live.txt`](./live.txt) · 2,104 条直播流 · 适用 TVBox / TiviMate / APTV / PotPlayer）
  ```text
  https://gh-proxy.org/https://raw.githubusercontent.com/niubihu1/tvbox/main/live.txt
  ```

<details>
<summary>🌐 备用加速节点与 GitHub 原始直连（主线超时或海外网络请点此展开）</summary>

* **备用加速线路（ghfast 节点）**（[`1.json`](./1.json)）：
  ```text
  https://ghfast.top/https://raw.githubusercontent.com/niubihu1/tvbox/main/1.json
  ```

* **GitHub 原始直连（无加速前缀，适合海外网络或透明代理）**：
  * `1.json`（单仓主力）
    ```text
    https://raw.githubusercontent.com/niubihu1/tvbox/main/1.json
    ```
  * `tv8.json`（精选多仓）
    ```text
    https://raw.githubusercontent.com/niubihu1/tvbox/main/tv8.json
    ```
  * `自用仓库.txt`（主流大仓天梯）
    ```text
    https://raw.githubusercontent.com/niubihu1/tvbox/main/自用仓库.txt
    ```
  * `live.txt`（独立直播）
    ```text
    https://raw.githubusercontent.com/niubihu1/tvbox/main/live.txt
    ```

</details>

---

## ✨ 为什么选择牛虎？

| 传统接口常见痛点 | 🐯 牛虎接口的工程解法 |
| :--- | :--- |
| **一打开前排全是要扫码的网盘，不买会员根本看不了** | **免登秒播前置**：前 20 席位全部锁定免扫码在线即开即播旗舰站，老人小孩打开即看；`#1` 统一配置中心一码授权即可全盘畅看 4K 原画。 |
| **冷门老剧搜不到、点进去只有一条线还卡死** | **全网聚搜大满贯**：**148 站** 显式开启快搜与聚搜换源（占比 **76%**，远超常规接口），并配有 **21 家无切片广告 CMS 采集大厂** 强力兜底。 |
| **上游突然删文件 404，或外链脚本跑路全站瘫痪** | **全链路双轨自托管**：主 Spider JAR 与全部 `JS/PY/JSON` 脚本规则均同步镜像归档至本仓库，彻底消灭外部域名单点失效风险。 |
| **接口用几天就大面积失效，无人维护只能到处重新找** | **云端日更保活**：GitHub Actions 每天 **04:25 / 16:25** 自动并发探活，自动剔除 404/500 死链、优选最低延迟网盘镜像并跟随上游新版。 |

---

## 📊 接口构成

基于 `EasyTV`（`easy11.27.png`）纯单 Spider 原生 DEX 底座（0 外挂 Jar），从全网 **200+** 存活单仓、**2,000+** 候选站源中自动测活、去重与剔除死链后组装而成：

| 模块 | 当前规格 | 核心说明 |
| :--- | :--- | :--- |
| **点播站源** | **195 站**（172 可搜 / 143 聚搜） | 在线免登 **97** + 4K 网盘 **37** + 无广告 CMS 采集 **22** + 特色专区 **39** |
| **首屏排位** | **豆瓣开屏 + 配置中心 + 旗舰在线连环阵** | `#0 豆瓣热播`、`#1 配置中心`、`#2 厂长影视` + 优质免登秒播旗舰矩阵 |
| **Spider 核心** | **`easy11.27.png` 官方直连 CDN（0 外挂 Jar）** | 腾讯云 EdgeOne 官方极速直连 CDN（附 `;md5;` 指纹），本地与仓库高可用双轨备份，免疫反代屏蔽 |
| **外部脚本库** | **`JS / PY / JSON` 规则全量自托管镜像** | 同步自托管镜像全部官方脚本与课堂规则，彻底消除外部域名单点失效 |
| **电视直播** | **14 路直播列表** / [`live.txt`](./live.txt) 2,104 流 | 含 **9 路实测可用公网直播** + 5 路本地飞羊（`127.0.0.1:35457`），带 EPG/台标 |
| **视频解析** | **15 路** | 首位通用 `Web` 聚合 + **14 路测速优选解析**（已自动过滤失效 `type: 1` 接口） |
| **观影配套** | **弹幕 + 去广告 + DoH** | 原生 `9978` 实时弹幕、**6 条**去广告切片规则、**7 组**抗污染 DoH |
| **工程兼容** | **零重复 Key · 零相对路径 · 全 ASCII URL** | `dupK=0`、`rel=0`、`nonAsc=0`，老旧盒子 OkHttp 稳定加载不崩溃 |

---

## 🛡️ 工程保障

```mermaid
flowchart LR
    A["全网抓取与本地基线<br/>200+ 单仓 / 2,000+ 候选站"] --> B["多维探活与自愈<br/>死链清零 · 镜像测速 · 脚本自托管"]
    B --> C["10 项 Gatekeeper 硬门禁<br/>字节码匹配 · 哈希一致 · 零冲突"]
    C --> D["同步交付本仓库<br/>1.json · live.txt · tv8.json · 自用仓库.txt"]
```

<details>
<summary>🔒 点击展开：Gatekeeper 10 项自动化门禁铁律明细</summary>

| 规则 | 检查项 | 守护内容 |
| :---: | :--- | :--- |
| **Rule 1** | **JSON 与唯一 Key** | 校验 `1.json` / `tv8.json` 合法性，严禁站点 Key 重复与 Git 冲突标记残留 |
| **Rule 2** | **首页导航与配置中心** | `#0` 必须为豆瓣热播且禁用 `filterable: 0`，`#1` 严格绑定配置中心 |
| **Rule 3** | **直播源完整性** | 校验官方综合 + 5 大飞扬及 `live.txt` 分类与有效流数量（剔除恶意劫持主机） |
| **Rule 4** | **免登秒播置顶** | 前 20 席位严禁被需扫码网盘源挤占，保证老人小孩开箱即点即播 |
| **Rule 5** | **4K 网盘防越界** | 主流网盘源完备，`ext.site` 严禁空数组与已知死链域名 |
| **Rule 6** | **纯单Spider与聚搜率** | 校验全仓 100% 纯单 Spider 原生架构（0 外挂 Jar），强制要求全站 `>= 100` 站同时开启搜索/快搜/换源 |
| **Rule 7** | **DEX 字节码零缺失** | 逐一核对站点 `api` 与本地活跃主 Spider JAR 内的真实类名，杜绝 `ClassNotFound` |
| **Rule 8** | **Spider 指纹校验** | 强制检验 `spider` 的 `;md5;` 与本地物理 JAR 文件严格一致 |
| **Rule 9** | **纯净链路与编码** | 严禁多层代理嵌套、XBPQ 冗余外挂 Jar、嗷呜源零残留与未 Punycode 转义的非 ASCII URL |
| **Rule 10** | **防闪退根结构与配套** | 严格 12 个标准根字段（剥离 `hosts`/`headers`），核验弹幕、规则、解析、DoH 与 Logo |

</details>

---

## 📥 客户端下载

> **选型一句话指南**：安卓电视/手机主力首选 **FongMi 影视**（流畅度与杜比支持最佳）；喜欢随时切换多条路线选 **影视仓 + `tv8.json`**；老旧低内存电视盒选 **TVBox Takagen99**。（电视多为 32 位 `armeabi_v7a`，新盒子/手机多为 64 位 `arm64_v8a`）

### 📺 电视 TV / 盒子端

| 播放器 | 推荐版本 | 特点 | 下载地址 |
| :--- | :---: | :--- | :--- |
| **FongMi 影视 (蜂蜜)** | `v5.9.0` | 开源口碑首选，原生 TV 架构、流畅且支持杜比 | [32位通用](https://gh-proxy.org/https://github.com/FongMi/Release/releases/download/5.9.0/leanback-armeabi_v7a.apk) ｜ [64位](https://gh-proxy.org/https://github.com/FongMi/Release/releases/download/5.9.0/leanback-arm64_v8a.apk) ｜ [夸克](https://pan.quark.cn/s/b55be5547a68) ｜ [UC](https://drive.uc.cn/s/f8e067cede5f4?public=1) |
| **TVBox Takagen99** | `20260227` | 轻量低内存，老旧安卓盒子兼容性好 | [32位通用](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/TVBox/TVBox_takagen99_20260227-1116-armeabi-generic-java.apk) ｜ [64位](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/TVBox/TVBox_takagen99_20260227-1116-arm64-generic-java.apk) |
| **月光宝盒 Max** | `20260926` | 界面美观，支持单仓/多仓切换 | [APK直链](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/%E5%BD%B1%E8%A7%86/%E6%9C%88%E5%85%89%E5%AE%9D%E7%9B%92/%E6%9C%88%E5%85%89%E5%AE%9D%E7%9B%92Max1017.apk) ｜ [夸克](https://pan.quark.cn/s/a2c78537f5df) ｜ [UC](https://drive.uc.cn/s/a993aa79c6984?public=1) |
| **影视仓 原版 TV** | `v6.2.10` | 原生支持多仓与 `tv8.json` 聚合切换 | [32位通用](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/%E5%BD%B1%E8%A7%86/%E5%BD%B1%E8%A7%86%E4%BB%93/%E5%BD%B1%E8%A7%86%E4%BB%93-TV6.2.10-32%E4%BD%8D.apk) ｜ [64位](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/%E5%BD%B1%E8%A7%86/%E5%BD%B1%E8%A7%86%E4%BB%93/%E5%BD%B1%E8%A7%86%E4%BB%93-TV6.2.10-64%E4%BD%8D.apk) ｜ [百度(a6g7)](https://pan.baidu.com/s/11RcWwauUQiWt_Ids_zs5Qw?pwd=a6g7) ｜ [夸克](https://pan.quark.cn/s/61d324167c07#/list/share) |

### 📱 手机 / 平板端

| 播放器 | 推荐版本 | 特点 | 下载地址 |
| :--- | :---: | :--- | :--- |
| **FongMi 影视 手机版** | `v5.9.0` | 触控手势、画中画与一键投屏体验最佳 | [64位](https://gh-proxy.org/https://github.com/FongMi/Release/releases/download/5.9.0/mobile-arm64_v8a.apk) ｜ [32位](https://gh-proxy.org/https://github.com/FongMi/Release/releases/download/5.9.0/mobile-armeabi_v7a.apk) ｜ [夸克](https://pan.quark.cn/s/b55be5547a68) ｜ [UC](https://drive.uc.cn/s/f8e067cede5f4?public=1) |
| **影视仓 手机平板优化版** | `v3.3.10` | 适配手机/平板横竖屏，支持多仓管理 | [APK直链](https://gh-proxy.org/https://raw.githubusercontent.com/youhunwl/TVAPP/main/%E5%BD%B1%E8%A7%86/%E5%BD%B1%E8%A7%86%E4%BB%93/%E5%BD%B1%E8%A7%86%E4%BB%93-%E6%89%8B%E6%9C%BA%E7%89%88%E5%B9%B3%E6%9D%BF3.3.10-64%E4%BD%8D.apk) ｜ [百度(a6g7)](https://pan.baidu.com/s/11RcWwauUQiWt_Ids_zs5Qw?pwd=a6g7) |

---

## 📖 三步导入

1. **打开设置**：打开电视端 **FongMi / TVBox / 影视仓**，进入 **「设置」➔「配置地址」**；
2. **手机扫码推送**（告别遥控器打字）：保证手机与电视处于同一 Wi-Fi，用手机浏览器或微信扫描屏幕二维码（或访问页面显示的 `http://192.168.x.x:9978`）；
3. **填入接口并确定**：粘贴上方主线地址并点击确定：
   ```text
   https://gh-proxy.org/https://raw.githubusercontent.com/niubihu1/tvbox/main/1.json
   ```

---

## 💡 常见问题

**Q1：播放偶发卡顿、只有声音没画面，或提示解码失败？**
* 在播放器 **「设置 ➔ 解码设置」** 中，将默认播放器或解码模式在 **IJK 硬解 / EXO** 之间切换尝试；4K 高码率片源建议优先开启硬解。

**Q2：如何使用 4K 原画网盘源（阿里 / 夸克 / UC）？**
* 切到首页第 2 位 **`🐯牛虎 ┃ 配置中心`**，用手机对应网盘客户端扫码登录授权一次即可全盘通用。

**Q3：提示“无法获取配置 / 下载超时”怎么办？**
* 运营商偶发污染 DNS 时，可将电视 Wi-Fi 的 DNS 改为 `223.5.5.5` 或 `119.29.29.29`；
* 也可切换为备用加速线路（ghfast 节点）：`https://ghfast.top/https://raw.githubusercontent.com/niubihu1/tvbox/main/1.json`。

**Q4：找不到极冷门老剧怎么办？**
* 默认全站已有 **143** 个开启聚搜的站点；如前排未命中，可继续向下滚动或直接启用排在后面的 **CMS 采集专区（暴风 / 红牛 / 量子 / 非凡等）**，或切至多仓列表 [`自用仓库.txt`](./自用仓库.txt) 中的其他线路补充。

**Q5：某个站源失效或有想加的片源怎么反馈？**
* 欢迎直接前往 [**Issues 问题反馈区**](https://github.com/niubihu1/tvbox/issues) 留言，我们会结合自动化探针及时排查修复。

---

## ⚖️ 免责声明

* 本项目所有配置、规则、解析与接口链接均整理自公开网络与开源社区，仅作个人技术研究与多媒体协议学习交流；
* 本仓库不制作、不存储任何音视频文件，亦不参与任何商业收费行为；如有版权或侵权问题请通过 Issue 联系删除。

<div align="center">

### ⭐ 如果这个项目帮到了你，欢迎点亮右上角 **Star** 收藏防走丢！

[![Star History Chart](https://api.star-history.com/svg?repos=niubihu1/tvbox&type=Date)](https://star-history.com/#niubihu1/tvbox&Date)

</div>
