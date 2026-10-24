# StudyFlow AI — AI-Powered Personalized Student Learning Platform

StudyFlow AI is a responsive student learning dashboard prototype designed to help learners discover learning resources, explore free-first courses, find internship portals, search for local learning spaces and organise study tasks in one place.

> **Current status:** Working front-end prototype. The product name and repository name differ: the repository is `StudyMap-AI`, while the interface is branded `StudyFlow AI`.

## Features

- **Learning discovery:** Search a curated starter catalogue of learning resources, then open official providers or run a broader web search.
- **Free-first courses:** Browse beginner-friendly programming, AI, data science and web-development courses. Paid certificate/access terms are labelled where applicable.
- **Internship discovery:** Quick links to recognised internship and open-source opportunity portals.
- **Nearby learning places:** Enter a city, area or PIN code and open a map/web search for libraries, training centres or other learning spaces. Location is not read automatically.
- **Study planner:** Add, complete and delete tasks, optionally assign due dates, and track completion progress.
- **English/Tamil interface labels:** A language selector changes selected navigation and welcome labels. Course content itself may remain in its original language.
- **Responsive design:** Desktop, tablet and mobile layouts.
- **Privacy-minded prototype:** Study tasks and language preference are stored in the current browser's local storage. No user account or backend is required for the demo.

## Run locally

No build step or package installation is required.

1. Clone or download this repository.
2. Open `index.html` in a modern browser.
3. For a local web server, run one of these commands from the project folder:

   **Python**
   ```bash
   python -m http.server 8000
   ```

   Then visit `http://localhost:8000`.

   **Node.js**
   ```bash
   npx serve .
   ```

## Project structure

```
StudyMap-AI/
├── index.html   # App layout and page shell
├── styles.css   # Responsive design system
├── app.js       # Navigation, resource catalogue, filters and planner
└── README.md    # Project guide
```

## Important limitations

This is a front-end prototype, not yet a production AI platform.

- The learning catalogue is curated and static; it is not a live index of the entire internet.
- Search links open external providers/search pages. The app does not scrape or guarantee the accuracy of third-party listings.
- Course prices, access rules, internship eligibility and deadlines can change. Verify details on official sites.
- Nearby search hands off to a map or web-search provider; it does not currently use a maps API or geolocation.
- Tamil support currently covers selected interface labels, not full translation of every screen or external course.
- Planner data is stored locally in the browser and does not sync between devices.
- There is no login, cloud database, AI/LLM integration, recommendation model or RAG pipeline yet. Do not enter sensitive personal information.

## Roadmap

1. Add automated tests and accessibility checks.
2. Build a secure backend and optional account-based task sync.
3. Connect a vetted live resource search/API with source attribution and expiry checks.
4. Add a language-aware AI tutor with citations and safe fallback behaviour.
5. Add a retrieval-augmented generation (RAG) pipeline over trusted study materials.
6. Add optional maps integration and clear consent for location-based results.
7. Add deployment instructions and continuous integration.

## Technology

- HTML5
- CSS3 (responsive layouts)
- Vanilla JavaScript (no framework dependency)
- Browser local storage for demo preferences and study tasks

## Responsible use

StudyFlow AI is a learning discovery aid. It does not guarantee that any course or internship is free, legitimate, open, or suitable for a particular student. Confirm details with the official provider and never pay a recruiter to secure an internship.

## License

No license has been added yet. Add a license file before permitting reuse or redistribution.
