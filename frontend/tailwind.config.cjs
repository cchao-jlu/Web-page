module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        sans: ["Source Sans 3", "ui-sans-serif", "system-ui"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular"]
      },
      colors: {
        ink: "#1c1a16",
        paper: "#fffaf2",
        clay: "#c06b2c",
        sage: "#2b7a6d",
        sand: "#f0e5d5"
      },
      boxShadow: {
        soft: "0 20px 40px rgba(60, 45, 20, 0.12)"
      }
    }
  },
  plugins: []
};
