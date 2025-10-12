# MonitorX - License Update to Apache 2.0

**Date**: October 11, 2025
**Change**: MIT License → Apache License 2.0

---

## ✅ Files Updated

### Core License Files
- ✅ **LICENSE** - Created with full Apache 2.0 license text
- ✅ **NOTICE** - Created with copyright and third-party attributions
- ✅ **pyproject.toml** - Updated license field to "Apache-2.0"
- ✅ **README.md** - Updated license section with Apache 2.0 text
- ✅ **CHANGELOG.md** - Updated license reference

### License Classification
- ✅ **pyproject.toml** - Updated classifier from "MIT License" to "Apache Software License"

---

## 📋 What Changed

### Before (MIT License)
```
License: MIT
- Simple, permissive
- No patent grant
- No trademark protection
```

### After (Apache 2.0 License)
```
License: Apache-2.0
- Permissive with patent grant
- Explicit patent protection
- Trademark protection
- Contribution terms defined
- Better for enterprise use
```

---

## 🎯 Why Apache 2.0?

### Advantages
1. **Patent Grant**: Explicit patent protection for users
2. **Enterprise-Friendly**: Preferred by many organizations
3. **Trademark Protection**: Protects the MonitorX name
4. **Contribution Clarity**: Clear terms for contributors
5. **Legal Clarity**: More detailed than MIT
6. **Compatible**: Compatible with most open source licenses
7. **Industry Standard**: Used by major projects (Kubernetes, Apache projects, etc.)

### Key Provisions
- ✅ Permission to use, modify, distribute
- ✅ Patent grant from contributors
- ✅ Trademark rights reserved
- ✅ Limitation of liability
- ✅ Disclaimer of warranty
- ✅ Contribution terms (Section 5)

---

## 📄 License Text Locations

### Full License
- **File**: `LICENSE`
- **Content**: Full Apache 2.0 license text
- **Lines**: 201 lines

### Copyright Notice
- **File**: `NOTICE`
- **Content**: Copyright statement and third-party attributions
- **Purpose**: Required by Apache 2.0 (Section 4.d)

### Project Metadata
- **pyproject.toml**: `license = {text = "Apache-2.0"}`
- **Classifier**: `License :: OSI Approved :: Apache Software License`

---

## 🔧 Optional: Add License Headers

A script has been created to add license headers to Python files:

```bash
python add_license_headers.py
```

This will add the following header to Python files:

```python
# Copyright 2025 MonitorX Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

**Note**: This is optional but recommended for Apache 2.0 compliance.

---

## 🔍 Verification

### Check License File
```bash
head -20 LICENSE
# Should show "Apache License Version 2.0, January 2004"
```

### Check NOTICE File
```bash
cat NOTICE
# Should show copyright and attribution notices
```

### Check pyproject.toml
```bash
grep -A 2 "license" pyproject.toml
# Should show: license = {text = "Apache-2.0"}
```

### Check README
```bash
grep -A 5 "License" README.md
# Should reference Apache License 2.0
```

---

## 📚 Apache 2.0 Key Terms

### What You Can Do
- ✅ Use commercially
- ✅ Modify the code
- ✅ Distribute
- ✅ Sublicense
- ✅ Use patent claims

### What You Must Do
- ✅ Include license and copyright notice
- ✅ Include NOTICE file if distributing
- ✅ State significant changes made
- ✅ Include original attribution notices

### What You Cannot Do
- ❌ Use trademarks without permission
- ❌ Hold liable
- ❌ Expect warranty

---

## 🤝 Contributing Under Apache 2.0

### For Contributors
All contributions are made under Apache 2.0 terms (Section 5):

> "Unless You explicitly state otherwise, any Contribution intentionally
> submitted for inclusion in the Work by You to the Licensor shall be
> under the terms and conditions of this License, without any additional
> terms or conditions."

This means:
- No CLA required (license terms are in Apache 2.0)
- Contributors grant patent license
- Contributors retain copyright
- Contributions become part of the project

### Contributor License Agreement (CLA)
Not required - Apache 2.0 Section 5 covers contribution terms.

---

## 🔗 Compatibility

### Compatible Licenses
Apache 2.0 is compatible with:
- ✅ MIT
- ✅ BSD (2-clause, 3-clause)
- ✅ Apache 2.0 (same license)
- ✅ GPL 3.0 (one-way: Apache → GPL)
- ✅ Most permissive licenses

### Incompatible Licenses
- ❌ GPL 2.0 (not compatible)
- ❌ GPL 2.0-only projects

---

## 📊 Third-Party Dependencies

All MonitorX dependencies remain under their original licenses:
- **FastAPI**: MIT License
- **InfluxDB Client**: MIT License
- **Streamlit**: Apache 2.0
- **httpx**: BSD License
- **pytest**: MIT License
- **Other dependencies**: See NOTICE file

These licenses are all compatible with Apache 2.0.

---

## ✅ Checklist

- [x] LICENSE file created with Apache 2.0 text
- [x] NOTICE file created with copyright
- [x] pyproject.toml updated (license field)
- [x] pyproject.toml updated (classifier)
- [x] README.md updated (license section)
- [x] CHANGELOG.md updated (license reference)
- [x] Third-party attributions listed in NOTICE
- [ ] Optional: Add headers to Python files (run script)

---

## 📖 Resources

- **Apache License 2.0**: https://www.apache.org/licenses/LICENSE-2.0
- **Apache License FAQ**: https://www.apache.org/foundation/license-faq.html
- **Choosing a License**: https://choosealicense.com/licenses/apache-2.0/
- **License Compatibility**: https://www.apache.org/legal/resolved.html

---

## 🎉 Summary

MonitorX has been successfully updated from MIT License to Apache License 2.0:

- ✅ Full license text in `LICENSE`
- ✅ Copyright notice in `NOTICE`
- ✅ Metadata updated in `pyproject.toml`
- ✅ Documentation updated
- ✅ Third-party attributions included

**The project is now licensed under Apache 2.0!**

---

**Copyright 2025 MonitorX Team**
**Licensed under the Apache License 2.0**
