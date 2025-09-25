import { createTheme } from '@mui/material/styles';

// Extend the theme to include tertiary color
declare module '@mui/material/styles' {
  interface Palette {
    tertiary: Palette['primary'];
    surface: {
      main: string;
      variant: string;
    };
    onSurface: {
      main: string;
      variant: string;
    };
    outline: {
      main: string;
      variant: string;
    };
  }
  interface PaletteOptions {
    tertiary?: PaletteOptions['primary'];
    surface?: {
      main: string;
      variant: string;
    };
    onSurface?: {
      main: string;
      variant: string;
    };
    outline?: {
      main: string;
      variant: string;
    };
  }
}

// Material Design 3 Expressive Theme
const theme = createTheme({
  palette: {
    mode: 'light', // MD3 Expressive is typically light mode for expressiveness
    primary: {
      main: '#0061a4', // MD3 primary blue
      light: '#5383ec',
      dark: '#003f74',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#6750a4', // MD3 secondary purple
      light: '#9a82db',
      dark: '#4f378a',
      contrastText: '#ffffff',
    },
    tertiary: {
      main: '#7d5800', // MD3 tertiary amber
      light: '#ffb95c',
      dark: '#5b4200',
      contrastText: '#ffffff',
    },
    error: {
      main: '#ba1a1a',
      light: '#ff897d',
      dark: '#93000a',
      contrastText: '#ffffff',
    },
    warning: {
      main: '#ff9800',
      light: '#ffb547',
      dark: '#c77700',
      contrastText: '#000000',
    },
    info: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
      contrastText: '#ffffff',
    },
    success: {
      main: '#4caf50',
      light: '#81c784',
      dark: '#388e3c',
      contrastText: '#ffffff',
    },
    background: {
      default: '#fef7ff', // MD3 surface
      paper: '#fef7ff',
    },
    surface: {
      main: '#fef7ff',
      variant: '#e7f0ff',
    },
    onSurface: {
      main: '#1a1c1e',
      variant: '#42474e',
    },
    outline: {
      main: '#72787e',
      variant: '#c4c7c5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '3.5rem',
      fontWeight: 400,
      lineHeight: 1.2,
      letterSpacing: '-0.01562em',
    },
    h2: {
      fontSize: '2.8125rem',
      fontWeight: 400,
      lineHeight: 1.2,
      letterSpacing: '0em',
    },
    h3: {
      fontSize: '2.25rem',
      fontWeight: 400,
      lineHeight: 1.2,
      letterSpacing: '0.00938em',
    },
    h4: {
      fontSize: '1.875rem',
      fontWeight: 400,
      lineHeight: 1.2,
      letterSpacing: '0.00735em',
    },
    h5: {
      fontSize: '1.5rem',
      fontWeight: 400,
      lineHeight: 1.2,
      letterSpacing: '0em',
    },
    h6: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.2,
      letterSpacing: '0.0075em',
    },
    body1: {
      fontSize: '1rem',
      fontWeight: 400,
      lineHeight: 1.5,
      letterSpacing: '0.00938em',
    },
    body2: {
      fontSize: '0.875rem',
      fontWeight: 400,
      lineHeight: 1.43,
      letterSpacing: '0.01071em',
    },
    button: {
      fontSize: '0.875rem',
      fontWeight: 500,
      lineHeight: 1.75,
      letterSpacing: '0.02857em',
      textTransform: 'none', // MD3 prefers no text transform
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 1.66,
      letterSpacing: '0.03333em',
    },
    overline: {
      fontSize: '0.75rem',
      fontWeight: 500,
      lineHeight: 2.66,
      letterSpacing: '0.08333em',
      textTransform: 'uppercase',
    },
  },
  shape: {
    borderRadius: 16, // MD3 prefers larger border radius for expressiveness
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 20, // Pill shape for expressiveness
          padding: '12px 24px',
          boxShadow: 'none', // Flat design
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)', // Subtle shadow on hover
          },
        },
        contained: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.12)', // Minimal shadow
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.12)', // Flat with minimal shadow
          border: '1px solid rgba(0, 0, 0, 0.08)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none', // No gradients, solid colors
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.12)',
        },
      },
    },
  },
});

export default theme;