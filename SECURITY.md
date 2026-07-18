# Security

## Data boundary

ProofRank is local-first. Do not commit real credentials, private analytics exports, user data, production backups, or raw customer content.

The bundled demo is synthetic. Generated `audit.json` files may contain source paths and audited page text, so keep real outputs outside public repositories. The static dashboard renderer deliberately excludes local input paths.

## Network boundary

Network access is disabled unless both `--crawl` and `--allow-network` are passed. Before crawling a live site, obtain authorization for the exact host and page limit and use a respectful delay.

## Mutation boundary

ProofRank does not edit CMS data, hosting, DNS, analytics, Search Console, redirects, canonicals, sitemaps, schema, or page content. Treat any future write capability as a separate product and security review.

## Reporting a vulnerability

Open a private security advisory in the GitHub repository after publication. Do not place secrets or sensitive audit data in a public issue.
