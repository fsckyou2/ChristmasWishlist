# Glossary: one word per idea

These are the only words the app shows people for each idea: in navigation, page titles, headings, buttons, badges,
flash messages, emails and the tour. Code, database and URL names (`Claim`, `proxy_wishlist`, `delegate`,
`/auth/login`, ...) are internal and stay as they are. `tests/test_terms.py` renders pages and emails and fails if a
retired word shows up.

| Idea | Say this | Never say |
|---|---|---|
| Your own list | **My Wishlist**. Entries are **items** ("Add item", "Edit item", "Delete"). | |
| Other people's lists | **Browse Wishlists** (nav and page). A person's list: **"{Name}'s Wishlist"**. Back link: **"← Browse Wishlists"**. | "All Users" |
| Reserving an item to give | Button **"I'll get this"**. If more than one is left: **"I'll get this ({n} left)"**, which opens a page titled **"I'll get this"** asking **"How many will you get?"**. | Claim Gift, Claim Item, Unclaim |
| After you reserve | **"✓ You're getting this"**, or **"✓ You're getting {n} of these"**, with an **Undo** button. Flash: **You're getting "{item}".** Undo flash: **Undone: you're no longer getting "{item}".** | You Claimed, Unclaimed |
| What other givers see | **"Claimed by {names}"** when everything is claimed. Partly claimed: **"{x} of {y} claimed"** plus "by {names}". | Fully Claimed, "x/y Claimed" |
| Two people about to get the same thing | On "I'll get this": **"🎁 Someone may already be getting this"**, then **"{item}" is already on this wishlist and {Name} is getting it.** Helpers, who don't see who claimed what, read **"and someone is already getting it"**. | |
| Your reserved gifts | **Gifts I'm Giving** (nav, page title, emails, tour). | My Gifts for Others, My Claims |
| Progress on a gift | **Bought → Arrived → Wrapped**. | Purchased, Received (as a status), Acquired |
| Hidden extra gift for someone | **surprise gift**. Button: **"Add a surprise gift"**. Form title: **"Add a surprise gift for {Name}"**. Badge for others: **"🎁 Surprise gift · hidden from {Name}"**. Badge for the person who added it: **"🎁 Your surprise gift · hidden from {Name}"**. | custom gift |
| List for someone without an account | Button and page: **"Start a list for someone"**, subtext **"For kids or anyone who won't log in."** Badge: **"No account yet"**. Admin page: **"Lists for Someone"**. Editing it: **"Edit list details"**. | proxy wishlist, Non-User, Pending Account |
| People who manage such a list | **Helpers**. Menu: **"Lists I Help With"**. Admin: **"Helpers for {Name}'s list"**, **"Add helper"**, **"Remove helper"**. Permissions: **"Can add items / Can edit items / Can remove items"**. | delegate, Manager, Manage Wishlists |
| Folding a duplicate into another item | **"Combine with…"**. Flash: **Combined with "{item}".** | Merge with |
| Moving a "list for someone" into the person's account | **"Link to account"**. Flash: **"{Name}'s list is now linked to {User}'s account."** | Merge proxy |
| Admin viewing as a user | **Impersonate / Stop impersonating** (unchanged). | |
| Sign-up links | **Invites**. Button: **"Create invite link"**. | Registration Invites |
| Daily email | Subject: **"What's new on the family wishlists"**. Setting: **"Email updates"**: **Every day**, **Once a week (Mondays)**, **Off**. | Wishlist Updates from Your Family, unsubscribe (on pages) |
| Browse Wishlists rows | **"{x} of {y} still available"**, a **"{n} new"** badge (added since your last visit), **"Nothing on the list yet"** with **"Send a reminder"** / **"Reminder sent {date}"**. | |
| Deleting | No "are you sure?". Flash: **Deleted "{item}" from My Wishlist.** with **Undo**; then **"{item}" is back.** | "This cannot be undone" |
| Gifts I'm Giving totals | **"{n} gifts for {p} people"**, the total spend, and **"{a} to buy · {b} to wrap · {c} done"**. | |
| Phone navigation | Tab bar: **My Wishlist**, **Browse Wishlists**, **Gifts I'm Giving**, **More**. | Menu |
| New year | Admin: **"Start Christmas {next year}"**. The form still asks which Christmas is being closed. Given gifts are archived silently (not shown on the site). | Start a New Season, Gifts You've Received, Past gifts |
| Logging in and out | Verbs: **"Log in"** and **"Log out"**. Emailed link: **magic link** ("Email me a magic link"). Also **password** and **passkey**. Page title: **"Log in"**. | Login (as a word people read), Logout, Sign in, Sign out |
| Your own list's layout | One page you edit in place: **"Add from a link"**, **Edit** / **"Save changes"**, **↑ ↓** and drag **⠿** to reorder. | Card View, Table View, Cards \| List |
| Top-priority item | **"★ Most wanted"** (shown first, with a star, to everyone shopping for the list). Also **Size** and **Colour**. | Favorite, priority |

## The privacy phrase

Wherever the app promises that something stays secret, it uses **"hidden from {Name}"**, or **"{Name} can't see …"**.
It is always **can't**, never "won't" or "will NOT". Examples:
- At the top of someone else's list: **"🔒 {Name} can't see what's claimed or by whom."**
- On the surprise-gift form: **"🔒 {Name} can't see this. It's hidden from {Name}'s list and emails. Everyone else
  sees it, marked as yours, so nobody gets it twice."**
