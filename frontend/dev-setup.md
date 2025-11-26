# Development Setup

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to http://localhost:3000

## Backend Connection

The frontend expects the Optimus backend to be running on `http://localhost:8000`. 

To start the backend:
```bash
cd ../
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python run_backend.py
```

## Development Features

- **Hot reloading** - Changes are reflected instantly
- **TypeScript checking** - Real-time type validation
- **ESLint** - Code quality checking
- **Auto-proxy** - API calls automatically routed to backend

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript checking
- `npm run format` - Format code with Prettier

## Environment Variables

Create a `.env.local` file for local overrides:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Troubleshooting

### Backend Connection Issues
- Ensure the backend is running on port 8000
- Check for CORS issues in browser console
- Verify API endpoints are accessible

### Build Issues
- Run `npm run type-check` to identify TypeScript errors
- Clear node_modules and reinstall if needed
- Check for peer dependency warnings

### Performance Issues
- Enable React DevTools for component profiling
- Check Network tab for slow API calls
- Monitor bundle size with build analysis