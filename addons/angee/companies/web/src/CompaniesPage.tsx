import * as React from "react";
import { Column, Field, Form, Group, List, ResourceList } from "@angee/ui";
import { useCompaniesT } from "./i18n";

const MODEL = "companies.Company";

const companiesList = (
  <List resource={MODEL}>
    <Column field="name" />
    <Column field="created_at" />
  </List>
);

/** The company tree: full create/edit/list/detail over `companies.Company`. */
export function CompaniesPage(): React.ReactElement {
  const t = useCompaniesT();
  return (
    <ResourceList resource={MODEL} placement="inline" routed>
      {companiesList}
      <Form resource={MODEL}>
        <Field name="name" title />
        <Group label={t("company.group.structure")} columns={2}>
          <Field name="parent" label={t("company.field.parent")} />
          <Field name="organization" label={t("company.field.organization")} />
        </Group>
      </Form>
    </ResourceList>
  );
}
