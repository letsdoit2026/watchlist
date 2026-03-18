name: Update Stock Prices
on:
  schedule:
    - cron: '0 1 * * 1-5'
  workflow_dispatch:
jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Fetch prices from Naver
        run: python update_prices.py
      - name: Commit and push prices.json
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add prices.json
          git diff --staged --quiet || git commit -m "Update prices $(date '+%Y-%m-%d %H:%M')"
          git push
