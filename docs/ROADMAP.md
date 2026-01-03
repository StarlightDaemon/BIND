# BIND Roadmap

## Project Philosophy

**BIND is designed to stay slim, focused, and maintainable.**

We prioritize:
- 📦 **Simplicity** - Do one thing well
- 🎯 **Focus** - Archive metadata, nothing more
- 🧹 **Minimal** - Keep codebase small and clean
- 📚 **Documentation** - Over feature bloat

---

## v1.1 - Polish (Optional)

**Goal**: Minor improvements to user experience

### Documentation
- [ ] Add screenshots to README
- [ ] Add example RSS feed XML in docs
- [ ] Video walkthrough of setup (optional)

### Testing
- [ ] Manual testing on different Proxmox versions
- [ ] Verify on Debian 11 and 13
- [ ] Test with more torrent clients

**Timeline**: When community feedback arrives  
**Priority**: Low (v1.0 is feature-complete)

---

## v1.2+ - Maintenance Only

**Goal**: Keep BIND working as dependencies update

### Maintenance Tasks
- [ ] Update dependencies as needed
- [ ] Fix bugs if reported
- [ ] Update docs based on feedback
- [ ] Security patches if needed

**No major features planned** - BIND does what it needs to do.

---

## Rejected Ideas

These features were considered but rejected to keep BIND focused:

❌ **Keyword Filtering** - Use torrent client's RSS filters instead  
❌ **Magnet Deduplication** - Not needed with daily files  
❌ **RSS Pagination** - 100 items is sufficient  
❌ **Database Storage** - Files are simpler and more reliable  
❌ **Web Authentication** - Use reverse proxy if needed  
❌ **Multi-source Support** - Focused on AudioBookBay only  
❌ **Download Management** - That's the torrent client's job  
❌ **Search Interface** - RSS feed is the interface  

---

## Design Principles Going Forward

1. **No Feature Creep** - Reject features that add complexity
2. **Delegate to Client** - Let torrent clients handle filtering/management
3. **Simple > Complex** - Daily text files > databases
4. **Documentation > Code** - Explain well rather than over-engineer
5. **Stability > Features** - Don't fix what isn't broken

---

## Contributing

If you'd like to propose a feature:
1. Open a GitHub issue first
2. Explain the use case
3. Why the torrent client can't handle it
4. Why it can't be a separate tool

We'll likely say no to maintain BIND's focus, but we're happy to discuss!

---

**BIND is feature-complete at v1.0.**

Future work is polish, testing, and maintenance only.
