import { createNamespaceT } from "@angee/ui";

export const enCompaniesMessages: Record<string, string> = {
  "company.field.parent": "Parent company",
  "company.field.organization": "Organization",
  "company.group.structure": "Structure",
};

export const useCompaniesT = createNamespaceT("companies", enCompaniesMessages);
