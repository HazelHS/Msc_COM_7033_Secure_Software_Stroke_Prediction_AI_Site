This project was created as part of my Msc course work for AI and data science at Leeds Trinity, for a full setup and usage guide, follow the instructions included in the "User Guide.docx" file. 
The "Design Documentation.docx" file contains a more complete explanation of how this project was planned and its specifications, however bellow contains exerts and a brief summary for convince.  

This Project was written in python as a working prototype of a website to demonstrate my understand of and development skills, in web development and secure software/security. 
The website was built to handle medical records, for both users (patients) and doctors (administrators) to upload, edit, amend and delete as each user and admin would expect with all the security and functionality one would expect of a project deployed in production environment.

Functionality:
1.	Well designed and user friendly home, login, registration, user settings, dashboard and individual records CRUD management pages.
2.	At least two roles, one for users and administrators, where admins have access to tools for overall records analysis and searches, and users are only able to CRUD their own records and delete their account and associated data if desired.

Data Protection and compliance:
1.	Limit data collection to only the necessarily required data for the needs of record analysis and website functionality.
2.	Comprehensive activity logging, for accountability.
3.	Secure retention and deletion procedures, ensure no third parties are able to access sensitive data with fail safety contingencies. 
4.	Use separate databases for user data, administrator user data, patient records and their respective audit logs, with encryptions at rest and for in transit for any sensitive data such as patient record ID’s, while maintaining search ability.

Security:
1.	Encoding & Sanitization: Use “Bleach” and “Flask-Talisman” to clean and sanitise user inputs. 
2.	Validation & Business Logic:  Use data validation on database CRUD (Create, Read, Update and Delete) operations to assure data is correctly typed and formatted safely.
3.	Web Frontend Security: Use “Flask-WTF” for “Cross-Site Request Forgery” (CSRF) protection and cookie tokens, and “Bleach” again for “Cross-Site Scripting” (XSS) protection.
4.	API & Web Service: Use “Flask Login” for secure session management and “limiter” for rate limiting.
5.	Authentication: Use “cryptography” and “Flash-Bcrypt” for strong password hashing and encryption.
6.	Authorisation: Create an elevated privilege role for an administrator, complete with audit logging. 
7.	Self‑contained Tokens: Use “Hash-Based Message Authentication Code” (HMAC), for deterministic “one-way” search ability.
8.	OAuth & OIDC: Use separated servers for resources, users and administrators along with their respective audit logging. 
9.	Cryptography: Covered with “cryptography”, use authenticated cryptography with fail safe on startup.
10.	Configuration: Use HTTPS with self-certifications or free certifications, and avoid using insecure HTTP connections,
12.	Data Protection: Use encryption at rest and in transit for all sensitive data to be stored on the databases.
13.	Secure Coding & Architecture: Perform threat modelling when appropriate and use “defensive coding” when possible.
14.	Security Logging & Error Handling: Use Secure logging, and audit.

Testing:
1.	Implement “Static Application Security Testing” (SAST) procedures, analysis the source code before deployment. Using tools such as ”Bandit” or “Semgrep” to check libraries for vulnerabilities or code for security mistakes.
2.	Implement “Dynamic Application Security Testing” (DAST) procedures, for catching runtime issues such as authentication flaws, poor server configurations and XSS/CSRF exploits, with tools such as “OSWAP ZAP”.
3.	Include comprehensive unit testing coverage and use Github build tests with Github actions if possible. 
