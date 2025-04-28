"""
Service for interacting with OpenAI’s Responses API to extract job information from URLs.
"""

from __future__ import annotations
import os
import json
from typing import Dict, Any
from datetime import datetime

import dotenv
from openai import OpenAI

# Load environment variables from .env file
dotenv.load_dotenv()


class OpenAIService:
    """Service for processing job URLs using OpenAI's Responses endpoint."""

    def __init__(self) -> None:
        """Initialize the OpenAI client and the JSON-Schema wrapper."""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # The JSON-Schema that describes the job posting object
        self._schema_body: Dict[str, Any] = {
            "type": "object",
            "properties": {
                "title":        {"type": "string"},
                "company":      {"type": "string"},
                "location":     {"type": "string"},
                "description":  {"type": "string"},
                "posting_date": {"type": ["string", "null"]},
                "salary":       {"type": ["string", "null"]},
                "source":       {"type": ["string", "null"]}
            },
            "required": [
                "title",
                "company",
                "location",
                "description",
                "posting_date",
                "salary",
                "source"
            ],
            "additionalProperties": False
        }

        # Wrapper expected by the Responses API
        self._text_format = {
            "format": {
                "type": "json_schema",
                "name": "job_posting",
                "schema": self._schema_body,
                "strict": True
            }
        }

    async def extract_job_info(self, url: str) -> Dict[str, Any]:
        """
        Extract job information from a URL.
        """
        prompt = (
            f"Please extract the job information from this job posting URL:\n{url}\n\n"
            "If you can't access the URL, make an educated guess based on the URL structure.\n"
            "Return the data following the specified schema with these guidelines:\n"
            "1. For the 'source' field, identify the job board or platform.\n"
            "2. If posting_date isn't explicit, estimate or use today's date.\n"
            "3. Keep description ≤ 500 words.\n"
            "4. If salary isn't available, omit it.\n"
        )

        try:
            # Responses endpoint call
            response = self.client.responses.create(
                model="gpt-4o",
                input=prompt,
                tools=[{"type": "web_search_preview"}],
                text=self._text_format
            )

            # Parse the structured JSON
            structured_data = json.loads(response.output_text)

            # Normalize posting_date
            date_str = structured_data.get("posting_date")
            if date_str:
                try:
                    structured_data["posting_date"] = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    structured_data["posting_date"] = datetime.now()
            else:
                structured_data["posting_date"] = datetime.now()

            return structured_data

        except Exception as e:
            return {
                "title": "",
                "company": "",
                "location": "",
                "description": f"Error extracting job info from {url}: {e}",
                "posting_date": datetime.now(),
                "source": "",
                "error": str(e)
            }
