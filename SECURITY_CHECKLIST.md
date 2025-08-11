# Security Checklist

Before committing to this repository, ensure you have completed the following security checks:

## ✅ Pre-Commit Security Review

### 1. **API Tokens & Credentials**
- [ ] No hardcoded API tokens in source code
- [ ] No hardcoded passwords in source code
- [ ] No hardcoded server URLs pointing to internal systems
- [ ] All sensitive values use environment variables or placeholders

### 2. **Environment Files**
- [ ] No `.env` files committed (check `.gitignore`)
- [ ] No `*_config.env` files committed
- [ ] Example files use placeholder values only

### 3. **Log Files**
- [ ] No log files committed (check `.gitignore`)
- [ ] Log files don't contain sensitive information
- [ ] Debug logging is disabled in production code

### 4. **Configuration Files**
- [ ] Example YAML files use placeholder values
- [ ] No real server URLs in configuration examples
- [ ] No real API keys in configuration examples

### 5. **Code Review**
- [ ] Search for common sensitive patterns:
  - `password`, `secret`, `key`, `token`
  - `api_key`, `bearer`, `auth`
  - Internal company URLs
  - Hardcoded credentials

## 🔍 **Search Commands**

Run these commands to verify no sensitive data remains:

```bash
# Search for potential API tokens
grep -r "MTMwMzQ2NDM3MjgxOlBrTox2iJRjAR" . --exclude-dir=.git

# Search for company URLs
grep -r "ext.net.nokia.com" . --exclude-dir=.git

# Search for potential secrets
grep -r -i "password\|secret\|key\|token\|api_key\|bearer\|auth" . --exclude-dir=.git

# Search for environment files
find . -name "*.env" -not -path "./.git/*"
```

## 🚨 **If You Find Sensitive Data**

1. **Immediately remove** the sensitive data
2. **Replace with placeholders** (e.g., `YOUR_API_TOKEN_HERE`)
3. **Check git history** - you may need to rewrite history if secrets were committed
4. **Rotate any exposed credentials** immediately
5. **Update this checklist** with lessons learned

## 📚 **Resources**

- [GitHub Security Best Practices](https://docs.github.com/en/code-security/security-advisories/security-advisories)
- [OWASP Security Guidelines](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)

## 🔐 **Emergency Contacts**

If you accidentally commit sensitive data:
1. **Immediately** force push a clean version
2. **Contact** your security team
3. **Rotate** any exposed credentials
4. **Document** the incident and lessons learned 