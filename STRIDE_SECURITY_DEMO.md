# STRIDE Security Implementation Demonstration Guide

This document provides step-by-step instructions to demonstrate each STRIDE security control implemented in the BantayBuntot application.

---

## 📋 Prerequisites

1. Install the new security dependencies:
```bash
pip install -r requirements.txt
```

2. Set up reCAPTCHA (optional but recommended for full demonstration):
   - Visit https://www.google.com/recaptcha/admin
   - Register your site (use reCAPTCHA v3)
   - Add keys to your `.env` file:
```
RECAPTCHA_PUBLIC_KEY=your-site-key
RECAPTCHA_PRIVATE_KEY=your-secret-key
```

3. Run migrations (if any):
```bash
python manage.py migrate
```

---

## 1. SPOOFING Protection (Identity Theft)

### Implemented Controls
- ✅ Secure session cookies (HTTPOnly, Secure, SameSite)
- ✅ Short-lived sessions (1 hour expiration)
- ✅ reCAPTCHA v3 on login/register
- ✅ Password strength enforcement
- ✅ Google OAuth 2.0/OIDC integration

### Demonstration Steps

#### A. Secure Cookie Verification

1. **Open browser developer tools** (F12) → Network tab
2. **Login to the application**
3. **Check response headers**:
   - Look for `Set-Cookie` header in the response
   - Verify the flags: `HttpOnly`, `Secure` (in production), `SameSite=Strict`
   
   Example:
   ```
   Set-Cookie: sessionid=xxx; HttpOnly; Secure; SameSite=Strict; Path=/
   ```

4. **Test cookie security**:
```javascript
// In browser console, try to access the cookie via JavaScript
document.cookie
// Should NOT show the sessionid cookie (it's HttpOnly)
```

#### B. Session Expiration Test

1. **Login and wait 1 hour** (or modify `SESSION_COOKIE_AGE` temporarily to 60 seconds for testing)
2. **Try to navigate** - should be redirected to login page
3. **Check logs**: Look for "Session expired" entries in `logs/audit.log`

#### C. reCAPTCHA Verification (if enabled)

1. **Open login page** with DevTools → Network tab
2. **Submit login form**
3. **Check POST request**:
   - Look for `captcha_token` in form data
   - Check response time (reCAPTCHA adds ~100-500ms)
4. **Check Google reCAPTCHA admin console** for traffic analytics

#### D. Rate Limiting on Login

1. **Try to login with wrong password 6 times** within 1 minute from the same IP
2. **On the 6th attempt**, you should see:
   - Error message: "Rate limit exceeded"
   - HTTP 429 status code
   - `X-RateLimit-Remaining: 0` header
3. **Check security logs**:
```bash
tail -f logs/security.log
```
Look for: `Rate limit exceeded for [IP]`

---

## 2. TAMPERING Protection (Data Modification)

### Implemented Controls
- ✅ HTTPS enforcement (production)
- ✅ HSTS headers (production)
- ✅ Content Security Policy (CSP)
- ✅ CSRF protection
- ✅ Security headers (X-Content-Type-Options, X-Frame-Options)

### Demonstration Steps

#### A. HTTPS/HSTS Headers (Production Mode)

1. **Set production environment**:
```bash
# Windows PowerShell
$env:DEBUG="False"
$env:ALLOWED_HOSTS="localhost,127.0.0.1"
python manage.py runserver
```

2. **Check security headers** using browser DevTools → Network → Response Headers:
   ```
   Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
   X-Content-Type-Options: nosniff
   X-Frame-Options: DENY
   Content-Security-Policy: default-src 'self'; ...
   ```

3. **Use online scanner** (e.g., https://securityheaders.com) to verify headers

#### B. CSRF Protection Test

1. **Attempt CSRF attack** by creating a malicious HTML file:
```html
<!-- csrf_attack_test.html -->
<form action="http://localhost:8000/api/reports/create/" method="POST" id="csrf-form">
    <input type="hidden" name="animal_type" value="cat">
    <input type="hidden" name="description" value="CSRF Attack Test">
</form>
<script>document.getElementById('csrf-form').submit();</script>
```

2. **Open this file** in browser while logged into BantayBuntot in another tab
3. **Result**: Request should fail with `403 Forbidden` (CSRF token missing)

#### C. CSP Violation Test

1. **Open browser console**
2. **Try to inject inline script** (paste in console):
```javascript
// This should be blocked by CSP
eval("alert('XSS')");
```
3. **Check console** for CSP violation warnings

---

## 3. REPUDIATION Protection (Denial of Action)

### Implemented Controls
- ✅ Immutable/append-only audit logging
- ✅ Security event logging with IP tracking
- ✅ Automatic audit log middleware
- ✅ Tamper-evident log entries (hash chains)

### Demonstration Steps

#### A. Immutable Audit Log Verification

1. **Perform actions** that should be logged:
   - Login
   - Create a report
   - Update profile
   - Logout

2. **Check the immutable audit log**:
```bash
type logs\immutable_audit.log
```

3. **Verify log format**:
```
2024-01-15T10:30:45.123456 | a1b2c3d4e5f6 | username | 192.168.1.100 | POST /login/ | status=200 duration=150.25ms
```

4. **Attempt to modify the log file**:
```bash
# Try to delete or modify (should fail due to permissions)
del logs\immutable_audit.log
# or
echo "tampered" > logs\immutable_audit.log
```

#### B. Security Event Alerting

1. **Trigger security events**:
   - Try 5 failed logins
   - Attempt to access admin panel as regular user
   - Try to delete your own account (admin self-delete)

2. **Check security logs**:
```bash
tail -20 logs\security.log
```

3. **Look for alert patterns**:
   - `SECURITY ALERT: Multiple failed logins`
   - `ADMIN_ACCESS_DENIED`
   - `ADMIN_SELF_DELETE_ATTEMPT`

#### C. Log Integrity Verification

1. **Calculate SHA256 hash** of log entries:
```python
# Python script to verify log integrity
import hashlib

with open('logs/immutable_audit.log', 'r') as f:
    for line in f:
        if '|' in line:
            parts = line.split(' | ')
            if len(parts) >= 2:
                stored_hash = parts[1]
                # Reconstruct entry without hash
                entry = ' | '.join([parts[0]] + parts[2:])
                calculated = hashlib.sha256(entry.encode()).hexdigest()[:16]
                print(f"Entry: {parts[0]}")
                print(f"Stored hash: {stored_hash}")
                print(f"Calculated:  {calculated}")
                print(f"Valid: {stored_hash == calculated}\n")
```

---

## 4. INFORMATION DISCLOSURE Protection (Data Leakage)

### Implemented Controls
- ✅ DEBUG mode controlled by environment variable
- ✅ Generic error messages in production
- ✅ No stack traces in production
- ✅ RBAC for data access
- ✅ Security headers prevent information leakage

### Demonstration Steps

#### A. DEBUG Mode Test

1. **Development mode** (DEBUG=True):
   - Trigger an error (visit non-existent URL like `/test-error/`)
   - You should see detailed Django error page with stack trace

2. **Production mode** (DEBUG=False):
```bash
$env:DEBUG="False"
python manage.py runserver
```
   - Visit the same error URL
   - You should see generic "Server Error (500)" page
   - No stack trace exposed

#### B. Rescuer Data Isolation Test

1. **Login as Rescuer A** and create/assign some reports
2. **Login as Rescuer B** in incognito window
3. **Try to access Rescuer A's reports** via API:
```bash
curl -H "Cookie: sessionid=[rescuer_b_session]" \
     http://localhost:8000/api/reports/[rescuer_a_report_id]/
```
4. **Result**: Should get "Permission denied" error

#### C. Admin Data Access Test

1. **Login as regular user**
2. **Try to access admin endpoints**:
   - `/admin-panel/`
   - `/admin-panel/api/users/delete/`
3. **Result**: Should be redirected to admin login or get 403 Forbidden

---

## 5. DENIAL OF SERVICE (DoS) Protection

### Implemented Controls
- ✅ Rate limiting on all critical endpoints
- ✅ Per-IP and per-user rate limiting
- ✅ CAPTCHA challenge for suspicious traffic
- ✅ File upload size limits (10MB)
- ✅ Rate limit headers in responses

### Demonstration Steps

#### A. API Rate Limiting Test

1. **Rapid API requests test**:
```bash
# Run this in PowerShell - try to create 10 reports in quick succession
for ($i = 1; $i -le 10; $i++) {
    curl -X POST http://localhost:8000/api/reports/create/ `
         -H "Content-Type: application/json" `
         -H "Cookie: sessionid=[your_session_id]" `
         -d '{"animal_type":"cat","description":"Test '$i'"}'
}
```

2. **Expected results**:
   - First 5 requests: Success (200 OK)
   - 6th+ request: `429 Too Many Requests`
   - Response headers include:
     ```
     X-RateLimit-Limit: 5
     X-RateLimit-Remaining: 0
     ```

#### B. Login Rate Limiting (Brute Force Protection)

1. **Simulate brute force attack**:
```bash
# Try 10 failed logins in quick succession
for ($i = 1; $i -le 10; $i++) {
    curl -X POST http://localhost:8000/ `
         -d "username=test@example.com&password=wrongpassword$i"
}
```

2. **After 5 attempts**: Rate limit kicks in
3. **Check security log**: Failed login attempts recorded

#### C. Upload Size Limit Test

1. **Try to upload large file** (>10MB):
   - Go to dashboard → Create report
   - Select image > 10MB
2. **Result**: Error message about file size limit

---

## 6. ELEVATION OF PRIVILEGE Protection (Unauthorized Access)

### Implemented Controls
- ✅ Admin role verification
- ✅ Self-deletion prevention
- ✅ Rescuer report isolation
- ✅ API endpoint RBAC
- ✅ Admin login CAPTCHA

### Demonstration Steps

#### A. Admin Access Control

1. **Login as regular user**
2. **Try to access admin panel**:
```bash
curl -H "Cookie: sessionid=[user_session]" http://localhost:8000/admin-panel/
```
3. **Result**: Redirect to admin login page

4. **Try admin API directly**:
```bash
curl -X POST http://localhost:8000/admin-panel/api/users/delete/ \
     -H "Content-Type: application/json" \
     -H "Cookie: sessionid=[user_session]" \
     -d '{"id":"some-user-id"}'
```
5. **Result**: 403 Forbidden

#### B. Self-Deletion Prevention

1. **Login as admin**
2. **Go to admin panel → Users**
3. **Try to delete your own account**
4. **Result**: Error message "Cannot delete your own account"
5. **Check security log**: `ADMIN_SELF_DELETE_ATTEMPT` logged

#### C. Rescuer Permission Boundaries

1. **Login as Rescuer A**
2. **Get assigned to a report**
3. **Note the report ID**
4. **Login as Rescuer B**
5. **Try to update the report assigned to Rescuer A**:
```bash
curl -X PUT http://localhost:8000/api/reports/[report_id]/update/ \
     -H "Content-Type: application/json" \
     -H "Cookie: sessionid=[rescuer_b_session]" \
     -d '{"status":"completed"}'
```
6. **Result**: "Permission denied. This report is assigned to another rescuer."

---

## 🔧 Automated Security Testing Script

Create a PowerShell script to automate basic security tests:

```powershell
# security_test.ps1

$baseUrl = "http://localhost:8000"
$results = @()

function Test-RateLimit {
    param($endpoint, $count = 10)
    $success = 0
    $limited = 0
    
    for ($i = 1; $i -le $count; $i++) {
        $response = Invoke-WebRequest -Uri "$baseUrl/$endpoint" -Method POST -Body "test=data" -SkipHttpErrorCheck
        if ($response.StatusCode -eq 429) { $limited++ }
        elseif ($response.StatusCode -eq 200) { $success++ }
    }
    
    return @{Success = $success; Limited = $limited}
}

# Test 1: Login rate limiting
Write-Host "Testing login rate limiting..."
$loginTest = Test-RateLimit "" 7
$results += "Login Rate Limit: $($loginTest.Limited) requests blocked out of 7"

# Test 2: Check security headers
Write-Host "Testing security headers..."
$response = Invoke-WebRequest -Uri $baseUrl -SkipHttpErrorCheck
$headers = $response.Headers
$results += "X-Frame-Options: $($headers['X-Frame-Options'])"
$results += "X-Content-Type-Options: $($headers['X-Content-Type-Options'])"

# Test 3: Check for debug mode
Write-Host "Testing debug mode..."
$errorResponse = Invoke-WebRequest -Uri "$baseUrl/nonexistent-url-trigger-404" -SkipHttpErrorCheck
$results += "Debug mode check: Status $($errorResponse.StatusCode)"

# Output results
Write-Host "`n=== Security Test Results ==="
$results | ForEach-Object { Write-Host $_ }
```

---

## 📊 Security Monitoring Dashboard

View security metrics in real-time:

1. **Check rate limiting status**:
```bash
# View recent rate limit events
grep "Rate limit" logs/security.log | tail -20
```

2. **View failed login attempts**:
```bash
# Count failed logins by IP
grep "LOGIN_FAILURE" logs/security.log | awk '{print $6}' | sort | uniq -c | sort -rn
```

3. **Check audit log integrity**:
```bash
# Count entries and check file size
wc -l logs/immutable_audit.log
ls -lh logs/immutable_audit.log
```

---

## 🎯 Quick Verification Checklist

Use this checklist to verify all security controls:

| STRIDE Category | Control | Verification Method | Status |
|-----------------|---------|---------------------|--------|
| **Spoofing** | HTTPOnly cookies | Browser DevTools → Application → Cookies | ☐ |
| **Spoofing** | Session expiration | Wait 1 hour, check if logged out | ☐ |
| **Spoofing** | reCAPTCHA | DevTools Network tab check for captcha_token | ☐ |
| **Tampering** | HTTPS redirect | Set DEBUG=False, check for HTTPS redirect | ☐ |
| **Tampering** | HSTS headers | DevTools → Response Headers | ☐ |
| **Tampering** | CSP headers | DevTools console for CSP violations | ☐ |
| **Tampering** | CSRF protection | Attempt cross-site POST request | ☐ |
| **Repudiation** | Audit log entries | Check logs/immutable_audit.log | ☐ |
| **Repudiation** | Log immutability | Try to delete/modify audit log file | ☐ |
| **Repudiation** | Security event logging | Perform suspicious activity, check security.log | ☐ |
| **Info Disclosure** | DEBUG=False | Trigger error, check for stack traces | ☐ |
| **Info Disclosure** | RBAC | Try to access other users' data | ☐ |
| **DoS** | Rate limiting | Make 10 rapid requests, check for 429 | ☐ |
| **DoS** | Upload limits | Try to upload >10MB file | ☐ |
| **Elevation** | Admin check | Try to access admin as regular user | ☐ |
| **Elevation** | Self-delete prevention | Try to delete own admin account | ☐ |
| **Elevation** | Rescuer isolation | Try to modify other rescuer's report | ☐ |

---

## 📝 Notes

- All rate limits reset after their time window (typically 1 minute)
- reCAPTCHA works invisibly (v3) - no checkbox required
- Audit logs should be backed up to external SIEM in production
- Some tests require production mode (DEBUG=False) to fully demonstrate

---

**Last Updated**: April 2024
**Version**: 1.0
