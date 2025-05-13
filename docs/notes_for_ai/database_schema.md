CREATE TABLE "jobs" (
	"id"	INTEGER,
	"job_id"	TEXT UNIQUE,
	"original_id"	TEXT,
	"title"	TEXT,
	"company"	TEXT,
	"blurb"	TEXT,
	"location"	TEXT,
	"salary"	TEXT,
	"site_name"	TEXT,
	"details_link"	TEXT,
	"posting_date"	TEXT,
	"job_description"	TEXT,
	"review_status"	TEXT,
	"rating_rationale"	TEXT,
	"rating_tldr"	TEXT,
	"star_rating"	TEXT,
	"hidden"	INTEGER DEFAULT 0,
	"company_id"	INTEGER,
	"slug"	TEXT,
	"hidden_date"	TEXT,
	"created_at"	TEXT,
	PRIMARY KEY("id"),
	FOREIGN KEY("company_id") REFERENCES "companies"("id")
)

// The history table is a bit outdated, but let's keep it around for now
CREATE TABLE history (
	id INTEGER PRIMARY KEY,
	company_id INTEGER,
	action TEXT,
	application_id INTEGER,
	job_id INTEGER,
	timestamp TEXT,
	FOREIGN KEY (company_id) REFERENCES companies(id),
	FOREIGN KEY (application_id) REFERENCES applications(id),
	FOREIGN KEY (job_id) REFERENCES jobs(id)
)

CREATE TABLE "companies" (
	"id"	INTEGER,
	"original_id"	TEXT,
	"name"	TEXT,
	"job_count"	INTEGER DEFAULT 0,
	"created_at"	TEXT,
	PRIMARY KEY("id")
)

// A job application is when the user applies to a job
CREATE TABLE "applications" (
	"id"	INTEGER,
	"original_id"	TEXT,
	"job_id"	INTEGER,
	"company_id"	INTEGER,
	"application_date"	TEXT,
	"notes"	TEXT,
	"created_at"	TEXT,
	"updated_at"	TEXT,
	PRIMARY KEY("id"),
	FOREIGN KEY("company_id") REFERENCES "companies"("id"),
	FOREIGN KEY("job_id") REFERENCES "jobs"("id")
)