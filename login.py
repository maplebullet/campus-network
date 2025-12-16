import urllib.request
import urllib.parse
import json
import time
import math
import hashlib
import hmac
import sys
import socket

# ================= 配置区域 =================
# 从 1.html 提取的配置
CONFIG = {
    "base_url": "http://10.145.255.21",
    "ac_id": "4",
    "enc_ver": "srun_bx1",
    "n": 200,
    "type": 1
}
# ==========================================

def _get_byte(c):
    return ord(c) if isinstance(c, str) else c

def _get_str(c):
    return chr(c) if isinstance(c, int) else c

class SrunAlgo:
    _base64Alpha = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"

    @staticmethod
    def s(a, b):
        c = len(a)
        v = []
        for i in range(0, c, 4):
            val = (_get_byte(a[i]) | 
                  (_get_byte(a[i + 1]) << 8 if i + 1 < c else 0) | 
                  (_get_byte(a[i + 2]) << 16 if i + 2 < c else 0) | 
                  (_get_byte(a[i + 3]) << 24 if i + 3 < c else 0))
            v.append(val)
        if b:
            v.append(c)
        return v

    @staticmethod
    def l(a, b):
        d = len(a)
        c = (d - 1) << 2
        if b:
            m = a[d - 1]
            if m < c - 3 or m > c:
                return None
            c = m
        
        s = []
        for i in range(d):
            s.append(_get_str(a[i] & 0xff))
            s.append(_get_str(a[i] >> 8 & 0xff))
            s.append(_get_str(a[i] >> 16 & 0xff))
            s.append(_get_str(a[i] >> 24 & 0xff))
        
        res = "".join(s)
        return res[0:c] if b else res

    @classmethod
    def xEncode(cls, msg, key):
        if msg == "": return ""
        v = cls.s(msg, True)
        k = cls.s(key, False)
        if len(k) < 4:
            k += [0] * (4 - len(k))
        
        n = len(v) - 1
        z = v[n]
        y = v[0]
        c = 0x86014019 | 0x183639A0
        m = 0
        e = 0
        p = 0
        q = math.floor(6 + 52 / (n + 1))
        d = 0
        
        while q > 0:
            q -= 1
            d = (d + c) & 0xFFFFFFFF
            e = (d >> 2) & 3
            for p in range(n):
                y = v[p + 1]
                m = (z >> 5 ^ (y << 2 & 0xFFFFFFFF))
                m += ((y >> 3 ^ (z << 4 & 0xFFFFFFFF)) ^ (d ^ y))
                m += (k[p & 3 ^ e] ^ z)
                z = v[p] = (v[p] + m) & 0xFFFFFFFF
            
            y = v[0]
            m = (z >> 5 ^ (y << 2 & 0xFFFFFFFF))
            m += ((y >> 3 ^ (z << 4 & 0xFFFFFFFF)) ^ (d ^ y))
            m += (k[n & 3 ^ e] ^ z)
            z = v[n] = (v[n] + m) & 0xFFFFFFFF
            
        return cls.l(v, False)

    @classmethod
    def base64Encode(cls, s):
        out = ""
        i = 0
        length = len(s)
        while i < length:
            c1 = _get_byte(s[i])
            i += 1
            if i == length:
                out += cls._base64Alpha[c1 >> 2]
                out += cls._base64Alpha[(c1 & 0x3) << 4]
                out += "=="
                break
            c2 = _get_byte(s[i])
            i += 1
            if i == length:
                out += cls._base64Alpha[c1 >> 2]
                out += cls._base64Alpha[((c1 & 0x3) << 4) | ((c2 & 0xF0) >> 4)]
                out += cls._base64Alpha[(c2 & 0xF) << 2]
                out += "="
                break
            c3 = _get_byte(s[i])
            i += 1
            out += cls._base64Alpha[c1 >> 2]
            out += cls._base64Alpha[((c1 & 0x3) << 4) | ((c2 & 0xF0) >> 4)]
            out += cls._base64Alpha[((c2 & 0xF) << 2) | ((c3 & 0xC0) >> 6)]
            out += cls._base64Alpha[c3 & 0x3F]
        return out

    @classmethod
    def get_encrypted_info(cls, info_obj, token):
        # 关键修正：使用 separators 去除 JSON 中的空格，与 JS JSON.stringify 保持一致
        json_str = json.dumps(info_obj, separators=(',', ':'))
        return "{SRBX1}" + cls.base64Encode(cls.xEncode(json_str, token))

def get_challenge(username):
    url = f"{CONFIG['base_url']}/cgi-bin/get_challenge?username={username}&ip=&callback=jQuery_&_={int(time.time()*1000)}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = response.read().decode('utf-8')
            # Extract JSON from JSONP
            start = data.find('(') + 1
            end = data.rfind(')')
            if start > 0 and end > 0:
                return json.loads(data[start:end])
    except Exception as e:
        print(f"Error getting challenge: {e}")
    return None

def login(username, password):
    print(f"[*] 正在尝试登录用户: {username}")
    
    # 1. Get Challenge
    res = get_challenge(username)
    if not res or 'challenge' not in res:
        print("[-] 获取 Challenge 失败，请检查网络连接")
        return

    challenge = res['challenge']
    client_ip = res['client_ip']
    print(f"[*] 获取 Challenge 成功: {challenge}, IP: {client_ip}")

    # 2. HMAC-MD5
    # JS: hmac_md5(password, challenge) -> key is password? No, JS implementation:
    # hmac_md5(key, data) -> bkey = str2bin(key)
    # In JS call: MiniCrypto.hmac_md5(p, res.challenge); -> key=password, data=challenge
    hmd5 = hmac.new(password.encode(), challenge.encode(), hashlib.md5).hexdigest()

    # 3. Info Encrypt
    info_obj = {
        "username": username,
        "password": password,
        "ip": client_ip,
        "acid": CONFIG['ac_id'],
        "enc_ver": CONFIG['enc_ver']
    }
    info = SrunAlgo.get_encrypted_info(info_obj, challenge)

    # 4. Checksum SHA1
    # JS: res.challenge + u + res.challenge + hmd5 + res.challenge + CONFIG.ac_id + res.challenge + res.client_ip + res.challenge + CONFIG.n + res.challenge + CONFIG.type + res.challenge + info
    chkstr = (challenge + username + challenge + hmd5 + challenge + 
              CONFIG['ac_id'] + challenge + client_ip + challenge + 
              str(CONFIG['n']) + challenge + str(CONFIG['type']) + challenge + info)
    chksum = hashlib.sha1(chkstr.encode()).hexdigest()

    # 5. Login Request
    params = {
        "action": "login",
        "username": username,
        "password": "{MD5}" + hmd5,
        "ac_id": CONFIG['ac_id'],
        "ip": client_ip,
        "chksum": chksum,
        "info": info,
        "n": CONFIG['n'],
        "type": CONFIG['type'],
        "os": "Windows 10",
        "name": "Windows",
        "double_stack": 0,
        "_": int(time.time()*1000),
        "callback": "jQuery_"
    }
    
    query_string = urllib.parse.urlencode(params)
    login_url = f"{CONFIG['base_url']}/cgi-bin/srun_portal?{query_string}"
    
    try:
        with urllib.request.urlopen(login_url, timeout=5) as response:
            data = response.read().decode('utf-8')
            if '"error":"ok"' in data:
                print("[+] 登录成功！")
            else:
                print(f"[-] 登录返回: {data}")
    except Exception as e:
        print(f"[-] 登录请求失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 login.py <username> <password>")
        sys.exit(1)
    
    u = sys.argv[1]
    p = sys.argv[2]
    login(u, p)
