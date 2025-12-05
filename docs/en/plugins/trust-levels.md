# Plugin Trust Levels

TonieToolbox uses a three-tier trust system to help you make informed decisions about plugin safety and reliability.

## Trust Levels

### 🏆 Official
**What it means:** Developed and maintained by the TonieToolbox core team.

**Security:**
- Thoroughly reviewed and tested
- Automatically approved for installation
- No security warnings
- Full compatibility guarantee

**Examples:** Plugin Manager GUI, built-in themes

---

### ✅ Verified
**What it means:** Community-developed plugins that have been reviewed and approved by TonieToolbox maintainers.

**Security:**
- Code reviewed by maintainers
- Security vetted
- Author has proven track record
- Info message on first installation

**How plugins get verified:**
1. Author submits plugin to marketplace
2. Maintainers review code for security issues
3. Plugin functionality is tested
4. Author is added to verified list
5. All future plugins from this author are automatically verified

---

### 👥 Community
**What it means:** Community-contributed plugins that haven't been verified yet.

**Security:**
- Not reviewed by maintainers
- May access your files and network
- Could contain security vulnerabilities
- Install at your own risk

**Security Warning:**
Community plugins require explicit user confirmation before installation. You'll see a warning dialog explaining the risks.

**Best Practices:**
- Only install from authors you trust
- Check the plugin's source code repository if available
- Read reviews and ratings from other users
- Start with official or verified plugins when possible

## Visual Indicators

In the Plugin Manager GUI, you'll see trust badges next to each plugin:

- **🏆 Official** - Gold badge with special background
- **✅ Verified** - Green badge with checkmark
- **👥 Community** - Gray badge with people icon

The installation confirmation dialog also displays the trust level, making it easy to see the security status before installing.

## Configuration

### Allow Unverified Plugins
By default, TonieToolbox allows installation of community plugins after showing a security warning. You can disable this in settings if you want to restrict installations to verified plugins only:

```toml
[plugins]
allow_unverified = false
```

### Verified Authors List
Maintainers manage the verified authors list. If you're a plugin developer and want to become verified:

1. Submit your plugin to the TonieToolbox plugin repository
2. Contact the maintainers via GitHub issues
3. Pass the code review process
4. Get added to the verified authors list

## For Plugin Developers

### How to Get Verified

1. **Build a Track Record:**
   - Create high-quality, well-documented plugins
   - Respond to user issues promptly
   - Follow TonieToolbox coding standards
   - Maintain your plugins actively

2. **Submit for Review:**
   - Open an issue in the TonieToolbox repository
   - Provide links to your plugin repositories
   - Explain your plugin's purpose and security measures
   - Be prepared for code review feedback

3. **Verification Process:**
   - Maintainers review your code for security issues
   - Test your plugin functionality
   - Check for malicious code or vulnerabilities
   - Verify your identity and contact information

4. **Maintenance Requirements:**
   - Keep plugins updated
   - Respond to security reports promptly
   - Follow responsible disclosure practices
   - Maintain code quality standards

### Losing Verification

Verified status can be revoked if:
- Security vulnerabilities are not fixed promptly
- Malicious behavior is detected
- Plugins are abandoned without notice
- Code quality degrades significantly

## Security Considerations

### What Plugins Can Do

Plugins run with the same permissions as TonieToolbox, which means they can:
- Read and write files on your system
- Make network requests
- Execute arbitrary code
- Access TonieToolbox's internal data
- Modify application behavior

### Protecting Yourself

1. **Review Before Installing:**
   - Check the trust level badge
   - Read the plugin description
   - Look for a source code repository
   - Check for user reviews/ratings

2. **Monitor Behavior:**
   - Watch what files the plugin accesses
   - Check network activity if concerned
   - Report suspicious behavior to maintainers

3. **Keep Updated:**
   - Update plugins regularly
   - Enable plugin update notifications
   - Review changelogs before updating

4. **Use Verified Plugins:**
   - Start with official plugins
   - Prefer verified over community
   - Build trust gradually

## Reporting Security Issues

If you discover a security issue in any plugin:

1. **Do NOT** publicly disclose the vulnerability
2. Contact the TonieToolbox maintainers privately via GitHub Security Advisories
3. Provide details about the vulnerability
4. Allow time for the issue to be fixed before public disclosure

Responsible disclosure helps keep the community safe!

## FAQ

**Q: Can I trust verified plugins completely?**
A: Verified plugins have been reviewed, but no system is perfect. Always exercise caution and report suspicious behavior.

**Q: How often are plugins re-reviewed?**
A: Major updates are reviewed. Continuous monitoring helps catch issues between reviews.

**Q: Can I become a verified author?**
A: Yes! Build quality plugins, contribute to the community, and apply for verification.

**Q: What if I need a feature only available in a community plugin?**
A: Evaluate the risk vs. benefit. Check the source code if available, and proceed cautiously.

**Q: How do I report a malicious plugin?**
A: Use GitHub Security Advisories or contact maintainers directly with evidence.

---

*Last updated: November 23, 2025*
