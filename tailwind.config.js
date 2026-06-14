/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        "tertiary-container": "#bb5a00",
        "surface-container-high": "#2a2933",
        "tertiary": "#ffb689",
        "on-secondary-fixed": "#3f001b",
        "inverse-primary": "#5340e7",
        "inverse-surface": "#e5e0ee",
        "surface-container": "#1f1f28",
        "on-tertiary": "#512300",
        "secondary-fixed": "#ffd9e1",
        "on-background": "#e5e0ee",
        "error-container": "#93000a",
        "background": "#13121c",
        "on-error": "#690005",
        "surface-dim": "#13121c",
        "surface-bright": "#393842",
        "primary-fixed-dim": "#c5c0ff",
        "outline-variant": "#474555",
        "tertiary-fixed": "#ffdbc8",
        "on-error-container": "#ffdad6",
        "on-primary-fixed-variant": "#3a1bd0",
        "on-primary-container": "#fffdff",
        "primary-fixed": "#e3dfff",
        "primary": "#c5c0ff",
        "on-tertiary-fixed-variant": "#743500",
        "on-surface": "#e5e0ee",
        "surface-variant": "#35343e",
        "outline": "#918ea1",
        "inverse-on-surface": "#302f39",
        "on-tertiary-container": "#fffdff",
        "secondary": "#ffb1c5",
        "secondary-fixed-dim": "#ffb1c5",
        "tertiary-fixed-dim": "#ffb689",
        "surface": "#13121c",
        "on-surface-variant": "#c8c4d8",
        "surface-container-lowest": "#0e0d16",
        "primary-container": "#6b5bff",
        "on-secondary-fixed-variant": "#8c0a46",
        "secondary-container": "#8c0a46",
        "on-secondary": "#650030",
        "surface-container-highest": "#35343e",
        "surface-container-low": "#1b1a24",
        "on-secondary-container": "#ff95b4",
        "error": "#ffb4ab",
        "on-primary-fixed": "#140067",
        "surface-tint": "#c5c0ff",
        "on-tertiary-fixed": "#311300",
        "on-primary": "#2500a2"
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px"
      },
      spacing: {
        "card-padding": "24px",
        "unit": "4px",
        "section-gap": "40px",
        "stack-gap": "16px",
        "container-padding": "20px"
      },
      fontFamily: {
        "display-lg-mobile": ["Plus Jakarta Sans"],
        "hero-num": ["Plus Jakarta Sans"],
        "label-caps": ["Inter"],
        "body-lg": ["Inter"],
        "hero-num-md": ["Plus Jakarta Sans"],
        "title-md": ["Inter"],
        "display-lg": ["Plus Jakarta Sans"]
      },
      fontSize: {
        "display-lg-mobile": ["28px", { lineHeight: "130%", fontWeight: "700" }],
        "hero-num": ["96px", { lineHeight: "110%", letterSpacing: "-0.04em", fontWeight: "800" }],
        "label-caps": ["12px", { lineHeight: "100%", letterSpacing: "0.05em", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "160%", fontWeight: "400" }],
        "hero-num-md": ["56px", { lineHeight: "110%", letterSpacing: "-0.04em", fontWeight: "800" }],
        "title-md": ["20px", { lineHeight: "150%", fontWeight: "600" }],
        "display-lg": ["32px", { lineHeight: "130%", fontWeight: "700" }]
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}
