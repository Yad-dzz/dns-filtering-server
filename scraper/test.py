from scraper import run_scraper

domains = ["example.com", "wikipedia.org"]
results = run_scraper(domains)

for domain, content in results.items():
    print(f"Extracted content from {domain}:\n{content[:500]}...\n")
