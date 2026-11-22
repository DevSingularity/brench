# Brench UI

The UI is a React 19.3.1 app built with Vite 8.3.8 and
`@vitejs/plugin-react` 6.3.0. It uses the Geist Variable local font assets and
local shadcn-style Button, Card, Badge, Select and Table primitives. Development
uses Node.js 20.19+ and pnpm 12+.

The demo does not need Node. Its built files in `dist/` are committed and
served by the Python harness. After changing UI source, run:

```sh
pnpm install --frozen-lockfile
pnpm build
```

The Vite development server proxies `/api` to the local Python server on port
8765. Fonts use system stacks so the built UI works without network access.
