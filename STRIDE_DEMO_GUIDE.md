# 🛡️ STRIDE Security Demo Guide (Simple & Visual)

## 1️⃣ SPOOFING - "Who Are You?"
**Threat:** Someone pretending to be you
**Demo:**
1. Go to login page
2. **Show:** CAPTCHA checkbox blocks bots from automated login attempts
3. **Try:** Login 6 times with wrong password
4. **Show:** Rate limit popup appears (blocks brute force)

**What to say:** "Without CAPTCHA, bots could try millions of passwords. The rate limit stops attackers after 5 attempts."

---

## 2️⃣ TAMPERING - "Did Someone Change This?"
**Threat:** Data being modified without permission
**Demo:**
1. Login as user
2. Go to "My Reports" page
3. **Show:** Try to edit someone else's report
4. **Result:** "Access Denied" - users can only edit THEIR OWN reports

**What to say:** "Even if someone gets your password, they can't modify other people's data. Each action checks: 'Is this YOUR data?'"

---

## 3️⃣ REPUDIATION - "Who Did What?"
**Threat:** Denying you did something / Can't trace actions
**Demo:**
1. **Show:** `logs/security.log` file
2. Every action is logged with:
   - Timestamp
   - User
   - IP Address
   - Action taken
3. Example: `[CAPTCHA_FAILURE] User: test@email.com | IP: 127.0.0.1 | Time: 2026-04-10 18:15:43`

**What to say:** "We log everything. If someone attacks us, we have proof of who, when, and what."

---

## 4️⃣ INFORMATION DISCLOSURE - "Who Can See This?"
**Threat:** Sensitive data leaking
**Demo:**
1. **Show:** Browser DevTools → Network tab
2. Look at any API request headers
3. **Show:** Response doesn't show other users' passwords or sensitive data
4. **Show:** `.env` file - secrets are hidden from code
5. **Show:** Password fields show dots (●●●●) not plain text

**What to say:** "Passwords are never shown in plain text. Secrets are in environment files, not in the code."

---

## 5️⃣ DENIAL OF SERVICE (DoS) - "System Overload"
**Threat:** Crashing the system with too many requests
**Demo:**
1. **Show:** Rate limiting already demonstrated in Spoofing
2. **Show:** CSP headers prevent malicious scripts
3. **Optional:** Try refreshing the page rapidly 100 times
4. **Result:** Server stays up, rate limits kick in

**What to say:** "Rate limiting stops one person from overwhelming the server. Even if 1000 bots attack, the system stays online."

---

## 6️⃣ ELEVATION OF PRIVILEGE - "Are You Admin Now?"
**Threat:** Normal user becoming admin
**Demo:**
1. Login as regular user
2. **Try:** Access admin URL: `http://127.0.0.1:8000/admin/`
3. **Result:** "403 Forbidden" or redirect to login
4. **Show:** Check user role in database - only 'admin' can access admin
5. **Show:** Middleware checks role on every request

**What to say:** "Even if you guess the admin URL, the system checks your role on EVERY request. Regular users can NEVER become admin by mistake."

---

## 🎯 Quick Summary for Judges

| Threat | What We Show | Protection |
|--------|--------------|------------|
| **S**poofing | CAPTCHA + Rate Limit | Bots can't login, brute force blocked |
| **T**ampering | Edit other user's report | Access control on every action |
| **R**epudiation | Security logs | Complete audit trail |
| **I**nfo Disclosure | Hidden passwords, .env secrets | Data never exposed |
| **D**oS | System stays up under load | Rate limiting |
| **E**levation | Can't access admin as user | Role verification on every request |

---

## 🔧 Files to Show

1. **CAPTCHA:** `templates/authentication/login.html` (lines 65-70)
2. **Rate Limit:** `authentication/views.py` (lines 17-26)
3. **Audit Logs:** `logs/security.log`
4. **Access Control:** `authentication/views.py` (lines 33-41)
5. **CSP Headers:** `BantayBuntot/security_middleware.py` (lines 32-45)
6. **Role Check:** `authentication/decorators.py` (role_required decorator)

---

## 🎤 Presentation Flow (5 minutes)

1. **Login Page** - Show CAPTCHA (30 sec)
2. **Fail CAPTCHA** - Show error persists, checkbox stays (30 sec)
3. **Login Successfully** - Show "My Reports" (30 sec)
4. **Try to Edit Other's Report** - Show access denied (30 sec)
5. **Show Logs** - Open security.log file (30 sec)
6. **Show .env** - Secrets are hidden (30 sec)
7. **Try Admin URL** - Show 403 forbidden (30 sec)
8. **Summary Slide** - All 6 STRIDE protections (2 min)
