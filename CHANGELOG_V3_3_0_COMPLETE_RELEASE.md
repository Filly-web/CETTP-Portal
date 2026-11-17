# V2.7 – Manual Tax Deadline Deletion

- Added a Delete action beside Edit for manually created tax compliance deadlines.
- Deletion requires a confirmation prompt and a CSRF-protected POST request.
- System-generated recurring statutory deadlines are not offered for deletion and are protected by the server route.
- Deleting a manual deadline also removes its linked evidence and detail audit entries through the existing ORM cascade relationships.
- No database schema changes or migration are required.
