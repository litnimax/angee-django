import { defineBaseAddon, resourcePageRoutes } from "@angee/app";
import { type BaseMenuItem } from "@angee/ui";
import { lazyRouteComponent } from "@tanstack/react-router";
import { Building } from "lucide-react";

import { enCompaniesMessages } from "./i18n";

// Companies overlay the parties rail rather than standing beside it: the
// operational company is the counterpart of the organization directory entry it
// links, so it belongs under the rail parties owns (the nexus precedent). A
// top-level root here would make a one-page app out of a structural directory.
const companiesMenu: readonly BaseMenuItem[] = [
  {
    id: "companies.companies",
    label: "Companies",
    route: "companies.companies",
    parentId: "parties",
    icon: "company",
  },
];

const companies = defineBaseAddon({
  id: "companies",
  routes: [
    ...resourcePageRoutes(
      "companies.companies",
      "/companies",
      lazyRouteComponent(() => import("./CompaniesPage"), "CompaniesPage"),
      "companies.Company",
    ),
  ],
  menus: companiesMenu,
  icons: { company: Building },
  i18n: { companies: enCompaniesMessages },
});

export default companies;
