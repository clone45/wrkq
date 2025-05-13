{
  "_id": {
    "$oid": "66786677bf08be11edaed04e"
  },
  "user_id": {
    "$oid": "664822157dbf1665f9136241"
  },
  "name": "Collect LinkedIn Jobs",
  "workflow": "{\n  \"steps\": [\n    {\n      \"action\": \"scrape_linkedin_search_results\",\n      \"urls\": [\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=software%20engineering%20manager\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=%22engineering%20manager%22\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=development%20manager\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=%22technical%20product%20manager%22\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=%22product%20manager%22\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&geoId=102277331&keywords=software%20engineering%20manager&location=San%20Francisco%2C%20California%2C%20United%20States\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&geoId=102277331&keywords=technical%20product%20manager&location=San%20Francisco%2C%20California%2C%20United%20States\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=%22Manager%20Software%20Development%22\",\n        \"https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=product%20engineer\"\n      ]\n    }\n  ]\n}",
  "__v": 0
}