# Racing Simple

A simplified horse racing data application.

**Repository**: https://github.com/aerichmo/racingsimple

## Project Structure

```
RacingSimple/
├── README.md
├── package.json
├── .env.example
├── .gitignore
├── src/
│   ├── app.js
│   ├── config/
│   ├── models/
│   ├── routes/
│   └── views/
└── public/
    ├── css/
    ├── js/
    └── index.html
```

## Getting Started

### Quick Start
```bash
# Clone the repository
git clone https://github.com/aerichmo/racingsimple.git
cd racingsimple

# Run the startup script
./start.sh
```

### Manual Setup
1. Install dependencies:
   ```bash
   npm install
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Start the application:
   ```bash
   npm start
   ```

The application will be available at: http://localhost:3000

## Features

- Simple racing data display
- Clean, minimal interface
- Easy to understand codebase

## Development

- Node.js with Express
- Vanilla JavaScript frontend
- CSS for styling