import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const config: Config = {
  title: "React 19 + FastAPI Frontend",
  tagline: "Modern, high-performance boilerplate developer documentation.",
  favicon: "img/favicon.ico",

  future: {
    v4: true,
  },

  // GitHub Pages configuration
  url: "https://mobitrendz.github.io",
  baseUrl: "/react-frontend-template/",
  organizationName: "mobitrendz",
  projectName: "react-frontend-template",

  onBrokenLinks: "warn",
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: "warn",
    },
  },

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          routeBasePath: "/", // Serve docs directly at the root URL
          editUrl:
            "https://github.com/mobitrendz/react-frontend-template/tree/develop/docs-site/",
        },
        blog: false, // Disable the blog feature
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: "dark",
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: "React 19 + FastAPI Template Docs",
      logo: {
        alt: "MobiTrendz Alt Logo",
        src: "img/logo.svg",
      },
      items: [
        {
          href: "https://github.com/mobitrendz/react-frontend-template",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Template Links",
          items: [
            {
              label: "Frontend Template Repo",
              href: "https://github.com/mobitrendz/react-frontend-template",
            },
            {
              label: "FastAPI Backend Template",
              href: "https://github.com/mobitrendz/fastapi-backend-template",
            },
            {
              label: "Expo Mobile App Template",
              href: "https://github.com/mobitrendz/expo-mobile-template",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} MobiTrendz. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
