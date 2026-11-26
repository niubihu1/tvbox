# coding=utf-8
# !/usr/bin/python
# QQ群：807916734 @Dc
import time
import requests
import json
from urllib.parse import quote, unquote, urljoin, urlparse
import re
import base64
import hashlib
import html as html_lib
import threading
from bs4 import BeautifulSoup
from base.spider import Spider


class CctvH5ESession:
    """CCTV H5E 解密会话（2026 新/旧两套 NAL 网格兼容）。

    关键点：type25 控制是否解密及 classic/new-mode 切换；type1/type5
    按 RBSP 网格处理 EPB，并在 NAL 变短后由 TS adaptation field 吸收长度差。
    """

    MASK32 = 0xFFFFFFFF
    TYPE5_BASE = (160, 192, 224, 256, 288, 320)

    def __init__(self):
        self.new_mode = False
        self.should_decrypt = False
        self.type1_start = 64
        self.type1_guard = 17
        self.type1_min_len = 129

    def reset(self):
        self.new_mode = False
        self.should_decrypt = False

    @classmethod
    def tea_decrypt_block(cls, block, key):
        if len(block) < 8 or len(key) < 16:
            return bytes(block)
        v0 = int.from_bytes(block[0:4], 'little')
        v1 = int.from_bytes(block[4:8], 'little')
        k0 = int.from_bytes(key[0:4], 'little')
        k1 = int.from_bytes(key[4:8], 'little')
        k2 = int.from_bytes(key[8:12], 'little')
        k3 = int.from_bytes(key[12:16], 'little')
        delta = 0x9E3779B9
        sm = (delta * 16) & cls.MASK32
        for _ in range(16):
            t1 = ((((v0 << 4) & cls.MASK32) + k2) & cls.MASK32) ^ ((v0 + sm) & cls.MASK32) ^ (((v0 >> 5) + k3) & cls.MASK32)
            v1 = (v1 - t1) & cls.MASK32
            t0 = ((((v1 << 4) & cls.MASK32) + k0) & cls.MASK32) ^ ((v1 + sm) & cls.MASK32) ^ (((v1 >> 5) + k1) & cls.MASK32)
            v0 = (v0 - t0) & cls.MASK32
            sm = (sm - delta) & cls.MASK32
        return v0.to_bytes(4, 'little') + v1.to_bytes(4, 'little')

    @classmethod
    def type5_stride_f5(cls, key6):
        if len(key6) < 6:
            return 0
        le = int.from_bytes(bytes(key6[:4]), 'little')
        idx = le % 6
        return cls.TYPE5_BASE[idx] | key6[idx]

    @classmethod
    def type5_stride_from_nal(cls, nal):
        if len(nal) < 11:
            return 0
        return cls.type5_stride_f5(nal[5:11])

    @classmethod
    def type1_stride_f1(cls, nal):
        if len(nal) < 7:
            return 0
        return cls.type5_stride_f5(nal[1:7])

    @staticmethod
    def _epbs(nal):
        return [i for i in range(max(0, len(nal) - 2)) if nal[i] == 0 and nal[i + 1] == 0 and nal[i + 2] == 3]

    @staticmethod
    def _r2e_full(nal):
        out = []
        i = 0
        n = len(nal)
        while i < n:
            if i + 2 < n and nal[i] == 0 and nal[i + 1] == 0 and nal[i + 2] == 3:
                out.extend((i, i + 1))
                i += 3
            else:
                out.append(i)
                i += 1
        return out

    @staticmethod
    def _drop_epb(nal, epbs):
        for e in reversed(epbs):
            if e + 2 < len(nal) and nal[e] == 0 and nal[e + 1] == 0 and nal[e + 2] == 3:
                del nal[e + 2]
        return nal

    @classmethod
    def decrypt_type5_new(cls, nal, stride):
        if len(nal) < 21 or stride < 8:
            return nal
        key = bytes(nal[5:21])
        epbs = []
        r2e = []
        i = 0
        n = len(nal)
        # 与官方 worker 的 type5 网格一致：末尾不足 3 字节不参与网格索引。
        while i + 2 < n:
            if nal[i] == 0 and nal[i + 1] == 0 and nal[i + 2] == 3:
                epbs.append(i)
                r2e.extend((i, i + 1))
                i += 3
            else:
                r2e.append(i)
                i += 1
        rbsp_len = len(r2e)
        k = 0
        while True:
            o = 64 + k * stride
            if o + 16 > rbsp_len or o + 8 > rbsp_len:
                break
            blk = bytes(nal[r2e[o + b]] for b in range(8))
            dec = cls.tea_decrypt_block(blk, key)
            for b in range(8):
                nal[r2e[o + b]] = dec[b]
            k += 1
        return cls._drop_epb(nal, epbs)

    @staticmethod
    def type1_fbit(w):
        w0 = (w >> 0) & 1
        w8 = (w >> 8) & 1
        w15 = (w >> 15) & 1
        w19 = (w >> 19) & 1
        w25 = (w >> 25) & 1
        w30 = (w >> 30) & 1
        w31 = (w >> 31) & 1
        t = w0 | w8
        return (w31 ^ w15 ^ t ^ (w8 & w19) ^ (w25 & (w0 ^ w19)) ^
                (w0 & (1 ^ w8) & w30) ^ ((1 ^ w0) & w19 & w30) ^
                (w25 & w30 & (w8 ^ w19))) & 1

    @staticmethod
    def type1_is_b_step(step):
        return step in (2, 8, 9, 10)

    @staticmethod
    def type1_flip_mask_from_header(hdr):
        b0, b1, b2 = hdr[0], hdr[1], hdr[2]
        m = 0
        def setb(i):
            nonlocal m
            m |= (1 << i)
        if b0 == 0x01 and b1 == 0xA8:
            if (b2 >> 7) & 1: setb(0)
            if (b2 >> 6) & 1: setb(1)
            if 1 ^ ((b2 >> 5) & 1): setb(2)
            if (b2 >> 4) & 1: setb(3)
            if (b2 >> 3) & 1: setb(4)
            if (b2 >> 1) & 1: setb(6)
            if (b2 >> 0) & 1: setb(7)
            setb(9); setb(12)
            return m
        if b0 == 0x61:
            if (b2 >> 1) & 1: setb(0)
            if (b2 >> 0) & 1: setb(1)
            if 1 ^ ((b2 >> 5) & 1): setb(2)
            if (b2 >> 3) & 1: setb(4)
            if (b2 >> 2) & 1: setb(5)
            if (b2 >> 1) & 1: setb(6)
            if (b2 >> 0) & 1: setb(7)
            if (b2 >> 3) & 1: setb(14)
            if (b2 >> 2) & 1: setb(15)
            return m
        # 2026-09 规则：0x9a/9b 与 0x9c..9f 两个子族分开处理。
        if (b0 & 0x1F) == 1 and (b1 & 0xF0) == 0x90:
            t = (b1 >> 2) & 1
            if (b2 >> 7) & 1: setb(0)
            if (b2 >> 6) & 1: setb(1)
            s2 = ((b0 >> 0) & 1) ^ ((b2 >> 5) & 1)
            if not t:
                s2 = 1 ^ ((b2 >> 5) & 1)
            if s2: setb(2)
            if (b2 >> 4) & 1: setb(3)
            if (b2 >> 3) & 1: setb(4)
            if (b2 >> 2) & 1: setb(5)
            if (b2 >> 1) & 1: setb(6)
            if (b2 >> 0) & 1: setb(7)
            if t:
                if (b0 >> 0) & 1:
                    setb(9); setb(10); setb(11); setb(12); setb(14)
                setb(13)
            else:
                setb(9); setb(10); setb(11); setb(12); setb(14)
            if (b1 >> 0) & 1: setb(15)
            return m
        return m

    @classmethod
    def type1_g_flips(cls, x, y, flip_mask):
        w = (x | (y << 16)) & cls.MASK32
        p1 = 0
        for step in range(16):
            fv = cls.type1_fbit(w) ^ ((flip_mask >> step) & 1)
            b = fv ^ (1 if cls.type1_is_b_step(step) else 0)
            p1 |= (b << (15 - step))
            w = ((w << 1) | b) & cls.MASK32
        return p1 & 0xFFFF

    @classmethod
    def decrypt_type1_new(cls, nal, stride, start=64, guard=17):
        if stride < 4 or len(nal) < 3:
            return nal
        hdr = bytes(nal[:3])
        epbs = cls._epbs(nal)
        r2e = cls._r2e_full(nal)
        rbsp_len = len(r2e)
        flip_mask = cls.type1_flip_mask_from_header(hdr)
        k = 0
        while True:
            o = start + k * stride
            if o + guard > rbsp_len or o + 4 > rbsp_len:
                break
            blk = [nal[r2e[o + j]] for j in range(4)]
            x = blk[0] | (blk[1] << 8)
            y = blk[2] | (blk[3] << 8)
            p1 = cls.type1_g_flips(x, y, flip_mask)
            out = (p1 & 0xFF, (p1 >> 8) & 0xFF, x & 0xFF, (x >> 8) & 0xFF)
            for j, v in enumerate(out):
                nal[r2e[o + j]] = v
            k += 1
        return cls._drop_epb(nal, epbs)

    @classmethod
    def decrypt_classic_grid(cls, nal):
        if len(nal) < 48:
            return nal
        epbs = cls._epbs(nal)
        r2e = cls._r2e_full(nal)
        if len(r2e) < 48:
            return nal
        key = bytes(nal[r2e[16 + b]] for b in range(16))
        k = 0
        while True:
            o = 32 + k * 80
            if o + 80 > len(r2e):
                break
            blk = bytes(nal[r2e[o + b]] for b in range(8))
            dec = cls.tea_decrypt_block(blk, key)
            for b in range(8):
                nal[r2e[o + b]] = dec[b]
            k += 1
        return cls._drop_epb(nal, epbs)

    def on_nal(self, nal):
        if not nal:
            return nal
        ntype = nal[0] & 0x1F
        if ntype == 25:
            self.should_decrypt = len(nal) >= 2 and nal[1] == 1
            if len(nal) >= 4 and nal[2] == 0x01:
                if nal[3] == 0x09:
                    self.new_mode = True
                elif nal[3] == 0x06:
                    self.new_mode = False
            return nal
        if ntype not in (1, 5) or not self.should_decrypt:
            return nal
        if not self.new_mode:
            return self.decrypt_classic_grid(nal)
        if ntype == 5:
            stride = self.type5_stride_from_nal(nal)
            return self.decrypt_type5_new(nal, stride) if stride >= 8 else nal
        if len(nal) < self.type1_min_len:
            return nal
        stride = self.type1_stride_f1(nal) or 511
        return self.decrypt_type1_new(nal, stride, self.type1_start, self.type1_guard)


class CctvH5EDecryptor:
    """MPEG-TS PES/NAL 重建器；输出长度保持与输入 TS 一致。"""

    def __init__(self, data, session=None, vpid=0x100):
        self.data = bytearray(data)
        self.session = session or CctvH5ESession()
        self.vpid = int(vpid)

    @staticmethod
    def _expand_af_steal(data, pkt_off, need):
        if need <= 0 or pkt_off + 188 > len(data):
            return 0
        afc = (data[pkt_off + 3] & 0x30) >> 4
        if afc == 1:
            af_len = min(max(0, need - 1), 182)
            steal = 1 + af_len
            old_payload = bytes(data[pkt_off + 4:pkt_off + 188])
            data[pkt_off + 3] = (data[pkt_off + 3] & 0xCF) | 0x30
            data[pkt_off + 4] = af_len
            if af_len > 0:
                data[pkt_off + 5] = 0
                if af_len > 1:
                    data[pkt_off + 6:pkt_off + 5 + af_len] = b'\xFF' * (af_len - 1)
            new_pl = 184 - steal
            start = pkt_off + 5 + af_len
            data[start:start + new_pl] = old_payload[:new_pl]
            return steal
        if afc in (2, 3):
            af_len = data[pkt_off + 4]
            pi = 5 + af_len
            if pi >= 188:
                return 0
            old_payload_len = 188 - pi
            add = min(need, old_payload_len, max(0, 182 - af_len))
            if add <= 0:
                return 0
            old_payload = bytes(data[pkt_off + pi:pkt_off + 188])
            data[pkt_off + 5 + af_len:pkt_off + 5 + af_len + add] = b'\xFF' * add
            new_af_len = af_len + add
            data[pkt_off + 4] = new_af_len
            new_pl = old_payload_len - add
            start = pkt_off + 5 + new_af_len
            data[start:start + new_pl] = old_payload[:new_pl]
            data[pkt_off + 3] = (data[pkt_off + 3] & 0xCF) | (0x20 if new_pl == 0 else 0x30)
            return add
        return 0

    @staticmethod
    def _find_video_pid(data, default=0x100):
        # CCTV 常用 0x100；若分片里能直接看到视频 PES 起始，则动态纠正。
        for off in range(0, len(data) - 188 + 1, 188):
            if data[off] != 0x47 or not (data[off + 1] & 0x40):
                continue
            afc = (data[off + 3] & 0x30) >> 4
            if afc in (0, 2):
                continue
            pi = 4 if afc == 1 else 5 + data[off + 4]
            if pi + 4 > 188:
                continue
            p = off + pi
            if data[p:p + 3] == b'\x00\x00\x01' and 0xE0 <= data[p + 3] <= 0xEF:
                return ((data[off + 1] & 0x1F) << 8) | data[off + 2]
        return default

    def _decrypt_ts_inplace(self):
        data = self.data
        if len(data) < 188:
            raise ValueError('not a MPEG-TS segment')
        vpid = self._find_video_pid(data, self.vpid)
        pes = bytearray()
        spans = []  # (packet_offset, payload_index, payload_len)

        def flush():
            nonlocal pes, spans
            if not pes:
                return
            base_skip = 0
            if len(pes) >= 9 and pes[0:3] == b'\x00\x00\x01':
                base_skip = 9 + pes[8]
            if base_skip > len(pes):
                pes = bytearray(); spans = []; return
            pes_hdr = bytes(pes[:base_skip])
            es = bytes(pes[base_skip:])

            starts = []
            i = 0
            n = len(es)
            while i + 3 < n:
                if i + 4 <= n and es[i:i + 4] == b'\x00\x00\x00\x01':
                    starts.append((i, 4)); i += 4
                elif es[i:i + 3] == b'\x00\x00\x01':
                    starts.append((i, 3)); i += 3
                else:
                    i += 1

            new_es = bytearray()
            cursor = 0
            for idx, (pos, sc) in enumerate(starts):
                end = starts[idx + 1][0] if idx + 1 < len(starts) else len(es)
                if cursor < pos:
                    new_es.extend(es[cursor:pos])
                new_es.extend(es[pos:pos + sc])
                if pos + sc < end:
                    nal = bytearray(es[pos + sc:end])
                    nal = self.session.on_nal(nal)
                    new_es.extend(nal)
                cursor = end
            if cursor < len(es):
                new_es.extend(es[cursor:])

            new_pes = bytearray(pes_hdr)
            new_pes.extend(new_es)
            capacity = sum(sp[2] for sp in spans)
            if capacity > len(new_pes):
                remaining = capacity - len(new_pes)
                for sp in reversed(spans):
                    if remaining <= 0:
                        break
                    remaining -= self._expand_af_steal(data, sp[0], remaining)
                new_spans = []
                for pkt_off, _, _ in spans:
                    afc = (data[pkt_off + 3] & 0x30) >> 4
                    if afc in (0, 2):
                        continue
                    pi = 4 if afc == 1 else 5 + data[pkt_off + 4]
                    if pi < 188:
                        new_spans.append((pkt_off, pi, 188 - pi))
                spans = new_spans

            off2 = 0
            for pkt_off, pi, pl in spans:
                remain = len(new_pes) - off2
                chunk = min(pl, max(0, remain))
                if chunk:
                    data[pkt_off + pi:pkt_off + pi + chunk] = new_pes[off2:off2 + chunk]
                if chunk < pl:
                    data[pkt_off + pi + chunk:pkt_off + pi + pl] = b'\xFF' * (pl - chunk)
                off2 += pl
            pes = bytearray(); spans = []

        for off in range(0, len(data) - 187, 188):
            if data[off] != 0x47:
                continue
            pid = ((data[off + 1] & 0x1F) << 8) | data[off + 2]
            if pid != vpid:
                continue
            pusi = bool(data[off + 1] & 0x40)
            afc = (data[off + 3] & 0x30) >> 4
            if afc in (0, 2):
                continue
            pi = 4 if afc == 1 else 5 + data[off + 4]
            if pi >= 188:
                continue
            if pusi:
                flush()
            pes.extend(data[off + pi:off + 188])
            spans.append((off, pi, 188 - pi))
        flush()
        return bytes(data)

    def decrypt_segment(self):
        return self._decrypt_ts_inplace()


class Spider(Spider):
    def __init__(self):
        self.meta = {
            "key": "华夏",
            "name": "直播",
            "type": 4,
            "api": "/video/华夏",
            "searchable": 1,
            "quickSearch": 1,
            "changeable": 0
        }
        self.http = requests.Session()
        self.http.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://tv.cctv.com/"
        })
        self._h5e_sessions = {}
        self._h5e_lock = threading.RLock()

    def getName(self):
        return self.meta["name"]

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "4K", "type_name": "4K"},
                {"type_id": "栏目大全", "type_name": "栏目大全"},
                {"type_id": "电视剧", "type_name": "电视剧"},
                {"type_id": "纪录片", "type_name": "纪录片"},
                {"type_id": "特别节目", "type_name": "特别节目"},
                {"type_id": "动画片", "type_name": "动画片"}
            ],
            "list": []
        }

    def homeVideoContent(self):
        pass

    def _category(self, cid, pg):
        pg = int(pg or 1)
        pagecount = 20 if cid == "栏目大全" else 24

        if cid == "动画片":
            url = f"https://api.cntv.cn/list/getVideoAlbumList?channelid=CHAL1460955899450127&area=&sc=&fc={quote(cid)}&letter=&p={pg}&n={pagecount}&serviceId=tvcctv&topv=1&t=json"
        elif cid == "纪录片":
            url = f"https://api.cntv.cn/list/getVideoAlbumList?channelid=CHAL1460955924871139&fc={quote(cid)}&channel=&sc=&year=&letter=&p={pg}&n={pagecount}&serviceId=tvcctv&topv=1&t=json"
        elif cid == "电视剧":
            url = f"https://api.cntv.cn/list/getVideoAlbumList?channelid=CHAL1460955853485115&area=&sc=&fc={quote(cid)}&year=&letter=&p={pg}&n={pagecount}&serviceId=tvcctv&topv=1&t=json"
        elif cid == "特别节目":
            url = f"https://api.cntv.cn/list/getVideoAlbumList?channelid=CHAL1460955953877151&channel=&sc=&fc={quote(cid)}&bigday=&letter=&p={pg}&n={pagecount}&serviceId=tvcctv&topv=1&t=json"
        elif cid == "栏目大全":
            url = f"https://api.cntv.cn/lanmu/columnSearch?fl=&fc=&cid=&p={pg}&n={pagecount}&serviceId=tvcctv&t=json&cb=ko"
        elif cid == "4K":
            url = f"https://api.cntv.cn/NewVideo/getLastVideoList4K?serviceId=cctv4k&cid=CHAL1558416868484111&p={pg}&n={pagecount}&t=jsonp&cb=Callback"
        else:
            return {"list": [], "page": pg, "pagecount": pg}

        try:
            response = self.http.get(url, timeout=12)
            response.raise_for_status()
            videos = []

            if cid == "4K":
                raw = response.text.strip()
                m = re.search(r'^[^(]+\((.*)\)\s*;?$', raw, re.S)
                if m:
                    raw = m.group(1)
                data = json.loads(raw).get("data", {}) or {}
                for item in data.get("list") or []:
                    last = item.get("last_video") or {}
                    videos.append({
                        "vod_id": f"{cid}###{item.get('title','')}###{last.get('url','')}###{item.get('image','')}###{item.get('id','')}###{last.get('title','')}###{item.get('sc','')}###{item.get('fc','')}",
                        "vod_name": item.get("title", ""),
                        "vod_pic": item.get("image", ""),
                        "vod_remarks": last.get("title", "")
                    })

            elif cid == "栏目大全":
                raw = response.text.strip()
                m = re.search(r'^[^(]+\((.*)\)\s*;?$', raw, re.S)
                if m:
                    raw = m.group(1)
                root = json.loads(raw)
                data = root.get("response", {}) or {}
                for vod in data.get("docs") or []:
                    last = vod.get("lastVIDE") or vod.get("lastVideo") or {}
                    # 新老接口字段并不完全一致。优先保存真正的 TOPC 栏目 ID；
                    # 没有时保留最后一期 GUID，详情阶段再从栏目网页解析 topicID/lmtopId。
                    column_id = (
                        vod.get("column_id") or vod.get("columnId") or
                        vod.get("topicID") or vod.get("topicId") or vod.get("ctid") or
                        last.get("topicID") or last.get("ctid") or ""
                    )
                    last_guid = last.get("videoSharedCode") or last.get("guid") or ""
                    website = vod.get("column_website") or vod.get("url") or ""
                    if not column_id:
                        mm = re.search(r'(TOPC[0-9A-Za-z]+)', website)
                        column_id = mm.group(1) if mm else ""
                    # 同时保留栏目 TOPC 和最后一期 GUID，避免新旧接口切换时丢失兜底。
                    ref_value = f"{column_id}@@{last_guid}"
                    videos.append({
                        "vod_id": f"{cid}###{vod.get('column_name','')}###{website}###{vod.get('column_logo','')}###{ref_value}###{vod.get('column_playdate','')}###{vod.get('column_brief','')}",
                        "vod_name": vod.get("column_name", ""),
                        "vod_pic": vod.get("column_logo", ""),
                        "vod_remarks": vod.get("column_playdate", "")
                    })

            else:
                data = response.json().get("data", {}) or {}
                for vod in data.get("list") or []:
                    videos.append({
                        "vod_id": f"{cid}###{vod.get('title','')}###{vod.get('url','')}###{vod.get('image','')}###{vod.get('id','')}###{vod.get('year','')}###{vod.get('actors','')}###{vod.get('brief','')}",
                        "vod_name": vod.get("title", ""),
                        "vod_pic": vod.get("image", ""),
                        "vod_remarks": vod.get("year", "")
                    })

            return {
                "list": videos,
                "page": pg,
                "pagecount": 9999 if len(videos) >= pagecount else pg,
                "limit": pagecount,
                "total": 999999
            }
        except Exception as e:
            print(f"Category error: {e}")
            return {"list": [], "page": pg, "pagecount": pg}

    def categoryContent(self, cid, pg, filter, extend):
        return self._category(cid, pg)

    def _extract_topic_id(self, value):
        if not value:
            return ""
        m = re.search(r'(TOPC[0-9A-Za-z]+)', str(value), re.I)
        return m.group(1) if m else ""

    def _resolve_column_topic(self, ref_id, column_url=""):
        """解析栏目 TOPC ID：接口直给 > 最后一期视频 ctid > 栏目网页 topicID/lmtopId。"""
        direct = self._extract_topic_id(ref_id) or self._extract_topic_id(column_url)
        if direct:
            return direct

        # 旧接口：lastVIDE.videoSharedCode -> videoinfoByGuid -> ctid
        if ref_id:
            try:
                r = self.http.get(
                    f"https://api.cntv.cn/video/videoinfoByGuid?guid={quote(str(ref_id))}&serviceId=tvcctv",
                    timeout=10
                )
                if r.ok:
                    obj = r.json()
                    for key in ("ctid", "topicID", "topicId", "column_id", "columnId"):
                        topic = self._extract_topic_id(obj.get(key))
                        if topic:
                            return topic
            except Exception as e:
                print(f"栏目 GUID 转 TOPC 失败: {e}")

        # 新版栏目主页经常直接暴露 topicID；旧版可能叫 lmtopId。
        if column_url and str(column_url).startswith("http"):
            try:
                r = self.http.get(column_url, timeout=12)
                html = r.text or ""
                patterns = [
                    r'\btopicID\b\s*[:=]\s*["\'](TOPC[0-9A-Za-z]+)["\']',
                    r'\btopicId\b\s*[:=]\s*["\'](TOPC[0-9A-Za-z]+)["\']',
                    r'\blmtopId\b\s*[:=]\s*["\'](TOPC[0-9A-Za-z]+)["\']',
                    r'\bcolumnId\b\s*[:=]\s*["\'](TOPC[0-9A-Za-z]+)["\']',
                    r'(TOPC[0-9A-Za-z]{8,})'
                ]
                for p in patterns:
                    m = re.search(p, html, re.I)
                    if m:
                        return m.group(1)
            except Exception as e:
                print(f"栏目网页解析 TOPC 失败: {e}")
        return ""

    def _column_episodes(self, topic_id, limit=100):
        if not topic_id:
            return []
        try:
            params = {
                "id": topic_id,
                "d": "",
                "p": 1,
                "n": limit,
                "sort": "desc",
                "mode": 0,
                "serviceId": "tvcctv",
                "t": "json"
            }
            r = self.http.get("https://api.cntv.cn/NewVideo/getVideoListByColumn", params=params, timeout=12)
            obj = r.json()
            return obj.get("data", {}).get("list", []) or []
        except Exception as e:
            print(f"栏目剧集获取失败: {e}")
            return []

    @staticmethod
    def _text_score(value):
        value = str(value or '')
        cn = len(re.findall(r'[\u4e00-\u9fff]', value))
        bad = sum(value.count(ch) for ch in ('Ã', 'Â', 'ã', 'æ', 'å', 'ç', 'é', 'è', '¤', '¥', 'ð', 'ï¿½'))
        return cn * 8 - bad * 4 - value.count('\ufffd') * 12

    @classmethod
    def _repair_mojibake(cls, value):
        """修复 CCTV 动画接口偶发的 UTF-8→Latin-1/CP1252 误解码。"""
        text = str(value or '')
        candidates = [text]
        cur = text
        for _ in range(2):
            made = []
            for enc in ('latin1', 'cp1252'):
                try:
                    made.append(cur.encode(enc).decode('utf-8'))
                except Exception:
                    pass
            if not made:
                break
            best = max(made, key=cls._text_score)
            candidates.extend(made)
            if cls._text_score(best) <= cls._text_score(cur):
                break
            cur = best
        return max(candidates, key=cls._text_score)

    @classmethod
    def _decode_js_text(cls, value):
        value = str(value or '').strip()
        if not value:
            return ''
        try:
            value = html_lib.unescape(value)
        except Exception:
            pass
        try:
            if '\\u' in value or '\\x' in value:
                # 仅在确有 JS 转义时处理，避免把已有中文重新编码坏。
                value = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), value)
                value = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), value)
        except Exception:
            pass
        value = cls._repair_mojibake(value)
        value = re.sub(r'<[^>]+>', '', value)
        value = value.replace('&nbsp;', ' ').replace('&amp;', '&')
        return re.sub(r'\s+', ' ', value).strip()

    @staticmethod
    def _json_utf8_response(response):
        """CCTV 个别接口 charset 头不可靠；JSON 标准内容优先按 UTF-8 解码。"""
        raw = response.content or b''
        for enc in ('utf-8-sig', 'utf-8', 'gb18030'):
            try:
                return json.loads(raw.decode(enc))
            except Exception:
                continue
        return response.json()

    def _episode_title(self, item, parent_title='', index=0):
        """取得剧集显示标题，避免动画接口把内部英文代码/GUID显示成集名。"""
        def clean(v):
            return self._decode_js_text(v)

        # 有些动画专辑 title 是内部代码，而 brief/videoTitle 才是实际中文标题。
        fields = ('video_title', 'videoTitle', 'episode_title', 'episodeTitle', 'name', 'brief', 'title')
        guid = str(item.get('guid') or '')
        parent_has_cn = re.search(r'[\u4e00-\u9fff]', parent_title or '') is not None
        for key in fields:
            title = clean(item.get(key, ''))
            if not title:
                continue
            compact = re.sub(r'[^A-Za-z0-9_-]', '', title)
            has_cn = re.search(r'[\u4e00-\u9fff]', title) is not None
            looks_code = (
                title == guid or
                re.fullmatch(r'(?:VIDE|TOPC|CHAL)?[A-Za-z0-9_-]{10,}', compact or '') is not None or
                (parent_has_cn and not has_cn and re.fullmatch(r'[A-Za-z0-9_.:-]+', title) is not None)
            )
            if not looks_code:
                return title

        ep = (item.get('episode') or item.get('episode_number') or item.get('episodeNo') or
              item.get('order') or item.get('sort') or item.get('num') or item.get('index'))
        if ep not in (None, ''):
            return '第{}集'.format(ep)
        # 最后宁可显示正确的集序号，也不再把未知英文内部代码显示给用户。
        return '第{}集'.format(index + 1)

    @staticmethod
    def _cn_number_to_int(text):
        """把常见中文集数（一、十二、二十三、一百零二）转换为整数。"""
        if not text:
            return None
        text = str(text).replace('〇', '零').replace('两', '二')
        digits = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                  '六': 6, '七': 7, '八': 8, '九': 9}
        units = {'十': 10, '百': 100, '千': 1000}
        if all(ch in digits for ch in text):
            try:
                return int(''.join(str(digits[ch]) for ch in text))
            except Exception:
                return None
        total = 0
        number = 0
        for ch in text:
            if ch in digits:
                number = digits[ch]
            elif ch in units:
                unit = units[ch]
                if number == 0:
                    number = 1
                total += number * unit
                number = 0
            else:
                return None
        return total + number

    def _short_episode_title(self, item, parent_title='', index=0):
        """电视剧/纪录片使用短集号，避免把“本集主要内容”整段显示在选集按钮。"""
        # 1) 明确的 episode 字段优先；不把 sort/index 直接当集号，避免分页序号误判。
        direct_fields = (
            'episode', 'episode_number', 'episodeNo', 'episode_no',
            'episodeNum', 'episode_num', 'serial', 'sequence'
        )
        for key in direct_fields:
            value = item.get(key)
            if value in (None, ''):
                continue
            m = re.search(r'\d{1,4}', str(value))
            if m:
                n = int(m.group(0))
                if 0 < n < 10000:
                    return '第{}集'.format(n)

        # 2) CCTV 常把“第N集”放在 title/videoTitle，甚至 brief 最后的括号里。
        text_fields = (
            'video_title', 'videoTitle', 'episode_title', 'episodeTitle', 'name',
            'title', 'brief', 'description', 'desc'
        )
        texts = []
        for key in text_fields:
            value = self._decode_js_text(item.get(key, ''))
            if value:
                texts.append(value)

        # 阿拉伯数字：第31集 / 第2期 / EP03 / E12。
        for text in texts:
            m = re.search(r'第\s*0*(\d{1,4})\s*([集期])', text, re.I)
            if m:
                return '第{}{}'.format(int(m.group(1)), m.group(2))
            m = re.search(r'(?<![A-Za-z])(?:EP|E)\s*0*(\d{1,4})(?!\d)', text, re.I)
            if m:
                return '第{}集'.format(int(m.group(1)))

        # 中文数字：第一集 / 第十二集 / 第二十三期。
        for text in texts:
            m = re.search(r'第\s*([零〇一二两三四五六七八九十百千]+)\s*([集期])', text)
            if m:
                n = self._cn_number_to_int(m.group(1))
                if n:
                    return '第{}{}'.format(n, m.group(2))

        # 3) 其次才尝试 order/num 等字段，并限制在合理集数范围内。
        for key in ('order', 'num'):
            value = item.get(key)
            if value in (None, ''):
                continue
            m = re.fullmatch(r'\s*0*(\d{1,4})\s*', str(value))
            if m:
                n = int(m.group(1))
                if 0 < n < 1000:
                    return '第{}集'.format(n)

        # 4) 最后宁可显示紧凑序号，不再显示整段简介。
        return '第{}集'.format(index + 1)


    def _documentary_episode_title(self, item, parent_title='', index=0):
        """纪录片显示“第N集 + 简短子标题”，避免只显示集号或整段简介。"""
        label = self._short_episode_title(item, parent_title, index)

        text_fields = (
            'video_title', 'videoTitle', 'episode_title', 'episodeTitle',
            'name', 'title', 'brief', 'description', 'desc'
        )
        texts = []
        for key in text_fields:
            value = self._decode_js_text(item.get(key, ''))
            if value and value not in texts:
                texts.append(value)

        parent = self._decode_js_text(parent_title or '')

        def clean_subtitle(value):
            value = self._decode_js_text(value)
            if not value:
                return ''
            # 去掉片名和常见包裹，官网常见格式：《秘境花园》第1集 火山上的花园 长白山
            if parent:
                value = value.replace('《{}》'.format(parent), ' ').replace(parent, ' ')
            value = re.sub(r'^\s*[：:|丨·•\-—_]+', '', value)
            value = re.sub(r'\s+', ' ', value).strip(' \t\r\n-—_:：|丨·•，,。；;()（）[]【】')
            # 长篇“本集主要内容”不是选集子标题。
            if not value or '本集主要内容' in value:
                return ''
            if not re.search(r'[A-Za-z0-9\u4e00-\u9fff]', value):
                return ''
            if len(value) > 36:
                return ''
            # 排除纯内部代码、GUID 和纯数字。
            compact = re.sub(r'[^A-Za-z0-9_-]', '', value)
            if re.fullmatch(r'(?:VIDE|TOPC|CHAL)?[A-Za-z0-9_-]{10,}', compact or ''):
                return ''
            if re.fullmatch(r'\d+', value):
                return ''
            return value

        # 优先从“第N集/期”后面截取官网式子标题。
        patterns = [
            r'第\s*0*\d{1,4}\s*[集期]',
            r'第\s*[零〇一二两三四五六七八九十百千]+\s*[集期]',
            r'(?<![A-Za-z])(?:EP|E)\s*0*\d{1,4}(?!\d)'
        ]
        for text in texts:
            for pattern in patterns:
                m = re.search(pattern, text, re.I)
                if not m:
                    continue
                subtitle = clean_subtitle(text[m.end():])
                if subtitle:
                    return '{} {}'.format(label, subtitle)

        # 有些接口把集号和子标题拆在不同字段里。此时从标题类字段中选一个短标题。
        preferred_fields = ('video_title', 'videoTitle', 'episode_title', 'episodeTitle', 'name', 'title')
        for key in preferred_fields:
            value = self._decode_js_text(item.get(key, ''))
            if not value:
                continue
            # 先移除其中的集号，再判断剩余部分是否能作为子标题。
            value2 = value
            for pattern in patterns:
                value2 = re.sub(pattern, ' ', value2, flags=re.I)
            subtitle = clean_subtitle(value2)
            if subtitle and subtitle != label:
                return '{} {}'.format(label, subtitle)

        return label

    def _parse_animation_page(self, page_url):
        if not page_url or not str(page_url).startswith('http'):
            return []
        try:
            rr = self.http.get(page_url, timeout=12)
            try:
                html = rr.content.decode('utf-8')
            except Exception:
                html = rr.text or ''
            patterns = [
                r"'title':\s*'(?P<title>.+?)',\s*'img':\s*'.+?',\s*'brief':\s*'.+?',\s*'url':\s*'(?P<url>https?://.+?)'",
                r"'title':\s*'(?P<title>.+?)'.+?'url':\s*'(?P<url>https?://.+?)'",
                r'<a[^>]+href="(?P<url>https?://[^"]+)"[^>]+title="(?P<title>[^"]+)"'
            ]
            seen = set()
            out = []
            for pattern in patterns:
                for m in re.finditer(pattern, html, re.S | re.I):
                    title = self._decode_js_text(m.group('title'))
                    url = m.group('url').replace('\\/', '/')
                    key = (title, url)
                    if not title or not url or key in seen:
                        continue
                    seen.add(key)
                    out.append('{}${}'.format(title, url))
                if len(out) >= 2:
                    break
            return out
        except Exception as e:
            print('动画页面剧集解析失败:', e)
            return []

    @staticmethod
    def _b64url_encode(value):
        return base64.urlsafe_b64encode(str(value).encode('utf-8')).decode('ascii').rstrip('=')

    @staticmethod
    def _b64url_decode(value):
        s = str(value or '')
        s += '=' * ((4 - len(s) % 4) % 4)
        return base64.urlsafe_b64decode(s.encode('ascii')).decode('utf-8')

    def _proxy_url(self, kind, url, **kwargs):
        try:
            base = self.getProxyUrl()
        except Exception:
            return ''
        if not base:
            return ''
        parts = ['type=' + quote(str(kind)), 'url=' + quote(self._b64url_encode(url))]
        for k, v in kwargs.items():
            parts.append('{}={}'.format(quote(str(k)), quote(str(v))))
        joiner = '&' if '?' in base else '?'
        return base + joiner + '&'.join(parts)

    @staticmethod
    def _replace_quality_keep_query(url, bitrate):
        if not url:
            return ''
        if '?' in url:
            path, query = url.split('?', 1)
            suffix = '?' + query
        else:
            path, suffix = url, ''
        path = re.sub(r'/hls/(?:main|450|850|1200|2000|3000|4000|8000)/', '/hls/{}/'.format(bitrate), path, count=1)
        path = re.sub(r'/(?:main|450|850|1200|2000|3000|4000|8000)\.m3u8$', '/{}.m3u8'.format(bitrate), path)
        return path + suffix

    def _h5e_url(self, data, bitrate=2000):
        manifest = (data or {}).get('manifest') or {}
        url = (data or {}).get('hls_h5e_url') or manifest.get('hls_h5e_url') or ''
        if not url:
            return ''
        return url if bitrate is None else self._replace_quality_keep_query(url, bitrate)

    def _proxy_h5e_m3u8(self, params):
        try:
            src = self._b64url_decode(params.get('url', ''))
            br = int(params.get('br') or 2000)
            try:
                expected = float(params.get('duration') or 0)
            except (ValueError, TypeError):
                expected = 0.0
            sid = str(params.get('sid') or hashlib.md5(src.encode('utf-8')).hexdigest()[:16])
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win32; x86) AppleWebKit/537.36 Chrome/116 Safari/537.36',
                'Referer': 'https://tv.cctv.com/'
            }

            # 先探测 2000，再探测原始 master。某些节目 2000 路径会
            # 回落为仅 120 秒的预览片段，此时必须继续探测完整列表。
            candidates = list(dict.fromkeys([self._replace_quality_keep_query(src, br), src]))
            current_url = ''
            body = ''
            saw_short_preview = False
            for candidate in candidates:
                try:
                    r = self.http.get(candidate, headers=headers, timeout=12, allow_redirects=True)
                    playlist = r.text or ''
                    if not r.ok or '#EXTM3U' not in playlist[:4096]:
                        continue
                    origin = r.url or candidate
                    streams = self.parse_m3u8(playlist, origin)
                    if not streams:
                        if self._is_full_playlist(playlist, expected):
                            body, current_url = playlist, origin
                            break
                        saw_short_preview = True
                        continue

                    # 由高到低检索接近 720P 的子流；一条失效或不足时长时
                    # 继续尝试其他变体，而不是将 120 秒的列表直接返回。
                    target_bandwidth = br * 1000
                    eligible = [item for item in streams if (item.get('bandwidth') or 0) <= target_bandwidth * 1.25]
                    # 已标注分辨率时拒绝优先使用低于 720 高度的变体；若 1200
                    # 档有独立 720P 子流则不改变此前正常客户端的码率选择。
                    hd = [item for item in eligible if item.get('height', 0) >= 720]
                    other_hd = [item for item in streams if item.get('height', 0) >= 720]
                    ordered = hd + [item for item in other_hd if item not in hd] + [
                        item for item in (eligible or streams) if item not in hd and item not in other_hd
                    ]
                    for item in ordered:
                        rr = self.http.get(item['url'], headers=headers, timeout=12, allow_redirects=True)
                        selected = rr.text or ''
                        if not rr.ok or '#EXTM3U' not in selected[:4096]:
                            continue
                        if not self._is_full_playlist(selected, expected):
                            saw_short_preview = True
                            continue
                        body, current_url = selected, rr.url or item['url']
                        break
                    if body:
                        break
                except Exception as e:
                    print('H5E 播放列表探测失败:', e)
                    continue

            if not body:
                status = 424 if saw_short_preview else 404
                return [status, 'text/plain', b'H5E complete playlist unavailable', {}]

            rewritten = []
            for line in body.splitlines():
                raw = line.strip()
                if not raw or raw.startswith('#'):
                    rewritten.append(line)
                    continue
                absolute = urljoin(current_url, raw)
                if '.m3u8' in raw.lower():
                    p = self._proxy_url('cctv_h5e_m3u8', absolute, br=br, sid=sid, duration=expected)
                else:
                    p = self._proxy_url('cctv_h5e_ts', absolute, sid=sid)
                rewritten.append(p or absolute)
            content = ('\n'.join(rewritten) + '\n').encode('utf-8')
            return [200, 'application/vnd.apple.mpegurl', content, {
                'Content-Type': 'application/vnd.apple.mpegurl',
                'Cache-Control': 'no-cache'
            }]
        except Exception as e:
            return [500, 'text/plain', ('H5E playlist error: ' + str(e)).encode('utf-8'), {}]

    def _proxy_h5e_ts(self, params):
        try:
            src = self._b64url_decode(params.get('url', ''))
            r = self.http.get(src, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win32; x86) AppleWebKit/537.36 Chrome/116 Safari/537.36',
                'Referer': 'https://tv.cctv.com/'
            }, timeout=20)
            r.raise_for_status()
            raw = r.content
            sid = str(params.get('sid') or hashlib.md5(src.encode('utf-8')).hexdigest()[:16])
            # HLS 分片通常按序读取；同一播放会话保持 type25 的模式状态。
            with self._h5e_lock:
                session = self._h5e_sessions.get(sid)
                if session is None:
                    session = CctvH5ESession()
                    self._h5e_sessions[sid] = session
                    # 防止长期运行时会话表无限增长。
                    if len(self._h5e_sessions) > 24:
                        for k in list(self._h5e_sessions.keys())[:-16]:
                            self._h5e_sessions.pop(k, None)
                dec = CctvH5EDecryptor(raw, session=session).decrypt_segment()
            return [200, 'video/mp2t', dec, {'Content-Type': 'video/mp2t', 'Cache-Control': 'no-cache'}]
        except Exception as e:
            print('H5E TS 解密失败:', e)
            return [502, 'text/plain', ('H5E decrypt error: ' + str(e)).encode('utf-8'), {}]

    def _detail(self, vid):
        parts = vid.split("###")
        if len(parts) < 5:
            return {"list": []}
        tid = parts[0]
        title = parts[1]
        last_video = parts[2]
        logo = parts[3]
        ref_id = parts[4]
        vod_year = parts[5] if len(parts) > 5 else ""
        actors = parts[6] if len(parts) > 6 else ""
        brief = parts[7] if len(parts) > 7 else (parts[6] if tid == "栏目大全" and len(parts) > 6 else "")

        if tid == "搜索":
            return {"list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": logo,
                "type_name": actors,
                "vod_year": vod_year,
                "vod_actor": "",
                "vod_content": "",
                "vod_play_from": "央视",
                "vod_play_url": f"{title}${last_video}"
            }]}

        video_list = []
        from_id = "央视"

        try:
            if tid == "栏目大全":
                ref_parts = ref_id.split("@@", 1)
                column_ref = ref_parts[0] if ref_parts else ""
                last_guid = ref_parts[1] if len(ref_parts) > 1 else ("" if column_ref.upper().startswith("TOPC") else column_ref)
                topic_id = self._extract_topic_id(column_ref)
                if not topic_id:
                    topic_id = self._resolve_column_topic(last_guid or column_ref, last_video)
                print("栏目解析:", title, column_ref, last_guid, "->", topic_id)
                items = self._column_episodes(topic_id, 100)
                video_list = [f"{it.get('title','')}${it.get('guid','')}" for it in items if it.get('guid')]

                # 最后一层兼容：TOPC 列表暂时失败时至少保留接口返回的最后一期可播放 GUID。
                if not video_list and last_guid:
                    video_list = [f"{title}${last_guid}"]
                from_id = "央视"

            elif tid == "4K":
                url = f"https://api.cntv.cn/NewVideo/getVideoListByAlbumIdNew?id={quote(ref_id)}&serviceId=cctv4k&p=1&n=100&mode=0&pub=1"
                res = self.http.get(url, timeout=12)
                items = self._json_utf8_response(res).get("data", {}).get("list", []) or []
                # 两个线路都显示「央视」，但通过播放 ID 标识 4K，避免被普通线路降清晰度。
                video_list = [f"{it.get('title','')}$cctv4k:{it.get('guid','')}" for it in items if it.get('guid')]
                from_id = "央视"

            else:
                service_id = "tvcctv"
                url = f"https://api.cntv.cn/NewVideo/getVideoListByAlbumIdNew?id={quote(ref_id)}&serviceId={service_id}&p=1&n=100&mode=0&pub=1"
                res = self.http.get(url, timeout=12)
                items = self._json_utf8_response(res).get("data", {}).get("list", []) or []

                # 动画片优先使用结构化 Album API。之前优先抓网页脚本时，页面 charset/
                # JS 字符串会把 UTF-8 中文误解成 Latin-1，正是“ã/æ/ç...”乱码的来源。
                if tid == "动画片":
                    video_list = [
                        f"{self._episode_title(it, title, idx)}${it.get('guid','')}"
                        for idx, it in enumerate(items) if it.get('guid')
                    ]
                    # API 暂时无数据时才回退旧动画页面，并在解析时强制 UTF-8 + 乱码修复。
                    if not video_list:
                        page_list = self._parse_animation_page(last_video)
                        if page_list:
                            video_list = page_list
                else:
                    if tid == "纪录片":
                        video_list = [
                            f"{self._documentary_episode_title(it, title, idx)}${it.get('guid','')}"
                            for idx, it in enumerate(items) if it.get('guid')
                        ]
                    elif tid == "电视剧":
                        video_list = [
                            f"{self._short_episode_title(it, title, idx)}${it.get('guid','')}"
                            for idx, it in enumerate(items) if it.get('guid')
                        ]
                    else:
                        video_list = [
                            f"{self._episode_title(it, title, idx)}${it.get('guid','')}"
                            for idx, it in enumerate(items) if it.get('guid')
                        ]

                if not video_list and last_video:
                    html_res = self.http.get(last_video, timeout=12)
                    if tid in ["电视剧", "纪录片"]:
                        pattern = r"'title':\s*'(?P<title>.+?)',\s*'brief':\s*'.+?',\s*'img':\s*'.+?',\s*'url':\s*'(?P<url>https:.+?)'"
                    else:
                        pattern = r'class="tp1"><a\s*href="(?P<url>https:.+?)"\s*target="_blank"\s*title="(?P<title>.+?)"'
                    matches = list(re.finditer(pattern, html_res.text, re.S))
                    if tid == "纪录片":
                        video_list = [
                            f"{self._documentary_episode_title({'title': self._decode_js_text(m.group('title'))}, title, idx)}${m.group('url')}"
                            for idx, m in enumerate(matches)
                        ]
                    elif tid == "电视剧":
                        video_list = [
                            f"{self._short_episode_title({'title': self._decode_js_text(m.group('title'))}, title, idx)}${m.group('url')}"
                            for idx, m in enumerate(matches)
                        ]
                    else:
                        video_list = [f"{self._decode_js_text(m.group('title'))}${m.group('url')}" for m in matches]

                if not video_list and last_video:
                    video_list = [f"{title}${last_video}"]
                from_id = "央视"

            return {"list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": logo,
                "type_name": tid,
                "vod_year": vod_year,
                "vod_actor": actors if tid != "栏目大全" else "",
                "vod_content": brief,
                "vod_play_from": from_id,
                "vod_play_url": "#".join(video_list)
            }]}
        except Exception as e:
            print(f"Detail error: {e}")
            return {"list": []}

    def detailContent(self, ids):
        return self._detail(ids[0])

    async def get_guid(self, url):
        try:
            if "http" not in url:
                return url

            response = self.http.get(url)
            match = re.search(r'var\s+guid\s*=\s*"(\w+)";', response.text)
            return match.group(1) if match else url
        except Exception as e:
            print(f"Get GUID error: {e}")
            return url

    def parse_m3u8(self, content, base_url=""):
        """解析 master m3u8，返回按清晰度/码率排序的可播放子流。"""
        lines = [line.strip() for line in (content or "").splitlines() if line.strip()]
        streams = []
        for i, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF"):
                continue
            if i + 1 >= len(lines):
                continue
            next_line = lines[i + 1]
            if next_line.startswith("#"):
                continue
            bandwidth_match = re.search(r"BANDWIDTH=(\d+)", line, re.I)
            resolution_match = re.search(r"RESOLUTION=(\d+)x(\d+)", line, re.I)
            bandwidth = int(bandwidth_match.group(1)) if bandwidth_match else 0
            width = int(resolution_match.group(1)) if resolution_match else 0
            height = int(resolution_match.group(2)) if resolution_match else 0
            streams.append({
                "bandwidth": bandwidth,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}" if width and height else "",
                "url": urljoin(base_url, next_line) if base_url else next_line
            })
        streams.sort(key=lambda x: (x["height"], x["width"], x["bandwidth"]), reverse=True)
        return streams

    def _resolve_guid(self, pid):
        """将央视页面 URL 转为 getHttpVideoInfo.do 所需的 guid/pid。"""
        if not isinstance(pid, str):
            return pid
        value = pid.strip()
        if not value.startswith("http"):
            return value
        try:
            html_res = self.http.get(value, timeout=8)
            # 兼容 var guid="..." / guid = '...' 等写法。
            patterns = [
                r'\bguid\s*=\s*["\']([A-Za-z0-9_-]+)["\']',
                r'["\']guid["\']\s*:\s*["\']([A-Za-z0-9_-]+)["\']'
            ]
            for pattern in patterns:
                match = re.search(pattern, html_res.text, re.I)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"解析页面获取guid失败: {e}")

        # 最后尝试从 URL 路径中提取较长的字母数字 ID。
        path = urlparse(value).path
        ids = re.findall(r'([A-Za-z0-9]{20,40})', path)
        return ids[-1] if ids else value

    def _video_info(self, guid):
        """获取央视播放信息。这里必须传已解析后的 guid，而不是原网页 URL。"""
        api_url = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do"
        tsp = str(int(time.time()))
        vn = "2049"
        uid = "826D8646DEBBFD97A82D23CAE45A55BE"
        # CCTV 当前网页/下载器使用动态 vc，固定旧 vc 虽可能返回数据，但会降低兼容性。
        vc = hashlib.md5((tsp + vn + "47899B86370B879139C08EA3B5E88267" + uid).encode("utf-8")).hexdigest().upper()
        params = {
            "pid": guid,
            "client": "flash",
            "im": "0",
            "tsp": tsp,
            "vn": vn,
            "vc": vc,
            "uid": uid,
            "wlan": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://tv.cctv.com",
            "Referer": "https://tv.cctv.com/",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        response = self.http.get(api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def _direct_bitrate_url(self, hls_url, bitrate, host=None):
        """
        把 .../asp/hls/main/.../main.m3u8 转成指定码率的子流。
        例如 2000=央视网页“超清”，CCTV-4K 可使用 4000 档。
        """
        if not hls_url or "/asp/hls/main/" not in hls_url:
            return ""
        clean = hls_url.split("?", 1)[0]
        clean = clean.replace("/asp/hls/main/", f"/asp/hls/{bitrate}/", 1)
        if clean.endswith("/main.m3u8"):
            clean = clean[:-len("/main.m3u8")] + f"/{bitrate}.m3u8"
        if host:
            parsed = urlparse(clean)
            clean = host.rstrip("/") + parsed.path
        return clean

    def _probe_m3u8_info(self, url, timeout=6):
        """返回 (m3u8正文, 最终URL)。会记录重定向后的真实地址。"""
        if not url:
            return "", ""
        try:
            headers = {
                "User-Agent": self.http.headers.get("User-Agent", "Mozilla/5.0"),
                "Referer": "https://tv.cctv.com/"
            }
            res = self.http.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            text = res.text or ""
            if res.status_code == 200 and "#EXTM3U" in text[:4096]:
                return text, res.url or url
        except Exception as e:
            print(f"检测播放地址失败: {url} -> {e}")
        return "", ""

    def _probe_m3u8(self, url, timeout=6):
        return self._probe_m3u8_info(url, timeout)[0]

    def _bitrate_candidate_ok(self, requested, text, final_url):
        """拒绝名义高码率实际被 302/内容回落到 450/850 的情况。"""
        combined = ((final_url or "") + "\n" + (text or "")[:12000]).lower()
        found = []
        for b in (200, 450, 850, 1200, 2000, 3000, 4000, 8000):
            if re.search(rf'/({b})(?:/|\.m3u8)', combined):
                found.append(b)
        if found and max(found) < requested:
            print(f"码率回落: 请求 {requested}, 实际发现 {found}, {final_url}")
            return False
        return True

    def _rewrite_hls_bitrate(self, url, bitrate):
        if not url:
            return ""
        clean, separator, query = url.partition("?")
        clean = re.sub(r'/asp/hls/(?:main|200|450|850|1200|2000|3000|4000|8000)/', f'/asp/hls/{bitrate}/', clean, count=1)
        clean = re.sub(r'/(?:main|200|450|850|1200|2000|3000|4000|8000)\.m3u8$', f'/{bitrate}.m3u8', clean)
        return clean + (separator + query if separator else "")

    def _pick_best_hls(self, data, prefer_4k=False):
        """
        4K 保持上一版已验证可用的高码率策略。
        普通明文 HLS 仅在 H5E 代理不可用时兜底，优先恢复原 1200 档顺序。
        """
        hls_url = (data or {}).get("hls_url") or ""
        if not hls_url:
            return ""

        play_channel = ((data or {}).get("play_channel") or "").upper()
        is_4k = prefer_4k or "CCTV-4K" in play_channel or "4K" in play_channel
        is_cctv16 = "CCTV-16" in play_channel

        # 先读官方 master；旧 TVBox CCTV 规则就是从 master 的真实子流路径改到 1200。
        master_text, master_final = self._probe_m3u8_info(hls_url)
        base_candidates = []
        if master_text and '#EXT-X-STREAM-INF' in master_text:
            for line in master_text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    base_candidates.append(urljoin(master_final or hls_url, line))
        if not base_candidates:
            base_candidates = [hls_url]

        if is_4k:
            # 保留你已经实测可播放、1080P 的 4K 策略。
            bitrates = [8000, 4000, 3000, 2000, 1200]
            hosts = [None, "https://hls.cntv.baishancdnx.cn", "https://newcntv.qcloudcdn.com"]
        elif is_cctv16:
            bitrates = [3000, 2000, 1200, 850]
            hosts = [None]
        else:
            # 恢复原文件的 1200→2000 探测顺序；这里只作为无法使用 H5E 时的降级路线。
            bitrates = [1200, 2000, 850]
            hosts = [None]

        tried = set()
        for bitrate in bitrates:
            for base in base_candidates + [hls_url]:
                candidate = self._rewrite_hls_bitrate(base, bitrate)
                if not candidate:
                    continue
                variants = [candidate]
                for host in hosts:
                    if not host:
                        continue
                    p = urlparse(candidate)
                    variants.append(host.rstrip("/") + p.path)
                for u in variants:
                    if u in tried:
                        continue
                    tried.add(u)
                    body, final_url = self._probe_m3u8_info(u)
                    if (body and self._bitrate_candidate_ok(bitrate, body, final_url)
                            and self._is_full_playlist(body, self._expected_video_duration(data))):
                        print(f"命中清晰度: {bitrate} -> {final_url or u}")
                        return final_url or u

        # Master 本身若含多变体，直接选最高的非低清子流。
        if master_text:
            streams = self.parse_m3u8(master_text, master_final or hls_url)
            for stream in streams:
                u = stream.get("url") or ""
                if not u:
                    continue
                body, final_url = self._probe_m3u8_info(u)
                if not body or not self._is_full_playlist(body, self._expected_video_duration(data)):
                    continue
                # 普通视频优先至少 720 宽高信息；没有 RESOLUTION 时按带宽排序。
                if stream.get("height", 0) >= 720 or stream.get("bandwidth", 0) >= 1000000:
                    return final_url or u
            # 找不到可验证的完整高清子流时保留主列表，让播放器自行协商。
            if streams:
                return master_final or hls_url

        return hls_url

    def _highest_chapter_url(self, data):
        """仅在 MP4 章节确实包含整期节目时，才使用章节 URL。

        CCTV 的 chapters3/chapters4 可能由多个 120 秒左右的分片组成。
        原实现直接返回首片，会导致《新闻联播》等长节目只能播两分钟。
        """
        video = (data or {}).get("video") or {}
        try:
            total = float(video.get("totalLength") or 0)
        except (TypeError, ValueError):
            total = 0
        for key in ("chapters4", "chapters3", "chapters2", "chapters", "lowChapters"):
            chapters = video.get(key) or []
            if not isinstance(chapters, list) or len(chapters) != 1:
                continue
            entry = chapters[0]
            if not isinstance(entry, dict) or not entry.get("url"):
                continue
            try:
                duration = float(entry.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0
            # 总时长已知时，拒绝只能覆盖前 120 秒的「预览式」分片。
            if total > 180 and duration > 0 and duration < total * 0.85:
                continue
            return entry["url"]
        return ""

    @staticmethod
    def _hls_playlist_duration(body):
        """HLS 媒体列表总时长；主播放列表/未知内容返回 0。"""
        if "#EXT-X-STREAM-INF" in (body or ""):
            return 0.0
        total = 0.0
        for value in re.findall(r'^#EXTINF:([0-9]+(?:\.[0-9]+)?)', body or "", re.M):
            try:
                total += float(value)
            except ValueError:
                pass
        return total

    @staticmethod
    def _expected_video_duration(data):
        try:
            return float(((data or {}).get('video') or {}).get('totalLength') or 0)
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def _is_full_playlist(cls, body, expected_duration):
        """拒绝已知明显短于正片的播放列表，不误杀没有时长信息的旧节目。"""
        if not expected_duration or expected_duration < 180:
            return True
        duration = cls._hls_playlist_duration(body)
        return not duration or duration >= expected_duration * 0.80

    def _play(self, flag, pid):
        try:
            # 「华夏」与「华夏4K」都显示为「央视」，改用内部播放 ID 保留 4K 标记。
            raw_pid = str(pid or "")
            is_4k = (flag == "华夏4K") or raw_pid.startswith("cctv4k:")
            if raw_pid.startswith("cctv4k:"):
                raw_pid = raw_pid[len("cctv4k:"):]
            guid = self._resolve_guid(raw_pid)
            print("播放ID:", pid, "-> GUID:", guid)

            if flag in ["央视", "华夏", "华夏4K", "华夏动画", "中央台", "CCTV"]:
                try:
                    data = self._video_info(guid)
                    print("播放信息:", json.dumps({
                        "title": data.get("title"),
                        "play_channel": data.get("play_channel"),
                        "hls_url": data.get("hls_url"),
                        "validChapterNum": (data.get("video") or {}).get("validChapterNum")
                    }, ensure_ascii=False))

                    if is_4k:
                        # 保持原来已经实机验证的 4K 高码率选择策略。
                        final_url = self._pick_best_hls(data, prefer_4k=True)
                        if not final_url:
                            final_url = self._highest_chapter_url(data)
                    else:
                        final_url = ""
                        expected = self._expected_video_duration(data)
                        # 保留原版在 OK影视和 TVBox 已实测为 720P 的 H5E 代理。
                        # 不能先选择 hls_url/asp/hls/2000：该旧接口可能把
                        # 名义高码率请求重定向到 270P/标清，上一版正是因此降质。
                        # 传入原始 master，代理先请求 1200 档，失败时还能
                        # 尝试 master 上其它完整子流（特别是新闻联播）。
                        h5e = self._h5e_url(data, None)
                        if h5e:
                            proxy_url = self._proxy_url(
                                'cctv_h5e_m3u8', h5e,
                                br=1200,
                                duration=expected,
                                sid=hashlib.md5(guid.encode('utf-8')).hexdigest()[:16]
                            )
                            if proxy_url:
                                return {
                                    'parse': 0,
                                    'url': proxy_url,
                                    'header': {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win32; x86) AppleWebKit/537.36 Chrome/116 Safari/537.36',
                                        'Referer': 'https://tv.cctv.com/'
                                    }
                                }

                        # 不支持 localProxy 的客户端：优先完整 MP4（不能只取
                        # chapters4 的第一个 120 秒切片），其次再尝试非 H5E HLS。
                        # 这是兼容性降级，并不保证央视旧 HLS 服务仍提供 720P。
                        chapter_url = self._highest_chapter_url(data)
                        if chapter_url:
                            try:
                                rr = self.http.get(chapter_url, headers={
                                    'User-Agent': self.http.headers.get('User-Agent', 'Mozilla/5.0'),
                                    'Referer': 'https://tv.cctv.com/'
                                }, stream=True, timeout=6, allow_redirects=True)
                                if rr.status_code in (200, 206):
                                    final_url = rr.url or chapter_url
                                rr.close()
                            except Exception:
                                pass
                        if not final_url:
                            final_url = self._pick_best_hls(data, prefer_4k=False)

                    if final_url:
                        return {
                            "parse": 0,
                            "url": final_url,
                            "header": {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                                "Referer": "https://tv.cctv.com/"
                            }
                        }
                except Exception as e:
                    print(f"获取高清视频信息失败: {e}")

            return {"parse": 1, "url": raw_pid}
        except Exception as e:
            print(f"播放错误: {e}")
            return {"parse": 1, "url": pid}

    def playerContent(self, flag, pid, vipFlags=''):
        return self._play(flag, pid)

    def _search(self, pg, wd):
        pg = pg or 1
        url = f"https://search.cctv.com/ifsearch.php?page={pg}&qtext={quote(wd)}&sort=relevance&pageSize=20&type=video&vtime=-1&datepid=1&channel=&pageflag=0&qtext_str={quote(wd)}"

        try:
            response = self.http.get(url)
            data = response.json()

            def clean_text(text):
                if not text:
                    return ''
                return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', text)).strip()

            videos = [{
                "vod_id": f"搜索###{clean_text(item['title'])}###{item['urllink']}###{item['imglink']}###{item['id']}###{clean_text(item['uploadtime'])}###{clean_text(item['channel'])}",
                "vod_name": clean_text(item["title"]),
                "vod_pic": item["imglink"],
                "vod_remarks": f"{clean_text(item['channel'])} · {clean_text(item.get('uploadtime', ''))}".strip()
            } for item in data.get("list", [])]

            return {
                "list": videos,
                "page": int(pg),
                "pagecount": 9999,
                "total": 999999
            }
        except Exception as e:
            print(f"Search error: {e}")
            return {"list": [], "page": 1, "pagecount": 1}

    def searchContent(self, key, quick, pg="1"):
        return self._search(int(pg), key)

    def searchContentPage(self, key, quick, pg):
        return self._search(int(pg), key)

    def localProxy(self, params):
        ptype = str(params.get("type", "")) if isinstance(params, dict) else ""
        if ptype == "cctv_h5e_m3u8":
            return self._proxy_h5e_m3u8(params)
        if ptype == "cctv_h5e_ts":
            return self._proxy_h5e_ts(params)
        if ptype == "m3u8":
            return self.proxyM3u8(params)
        elif ptype == "media":
            return self.proxyMedia(params)
        elif ptype == "ts":
            return self.proxyTs(params)
        return None

