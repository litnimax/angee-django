import * as React from "react";
import { Column, Field, Form, Group, List, ResourceList } from "@angee/ui";

import { usePartiesT } from "./i18n";

/** Reusable bank directory and party-owned payment destinations. */
export function BanksPage(): React.ReactElement {
  const t = usePartiesT();
  return (
    <ResourceList resource="parties.Bank" placement="inline" routed>
      <List resource="parties.Bank">
        <Column field="name" />
        <Column field="bic" />
        <Column field="country" />
      </List>
      <Form resource="parties.Bank">
        <Field name="name" title />
        <Group label={t("bank.details")} columns={2}>
          <Field name="bic" label={t("bank.bic")} />
          <Field name="country" label={t("bank.country")} />
        </Group>
        <Field name="is_archived" />
      </Form>
    </ResourceList>
  );
}

export function BankAccountsPage(): React.ReactElement {
  const t = usePartiesT();
  return (
    <ResourceList resource="parties.BankAccount" placement="inline" routed>
      <List resource="parties.BankAccount">
        <Column field="account_number" />
        <Column field="party" />
        <Column field="bank" />
        <Column field="currency" />
        <Column field="is_archived" />
      </List>
      <Form resource="parties.BankAccount">
        <Field name="account_number" title label={t("bankAccount.number")} />
        <Group label={t("bankAccount.details")} columns={2}>
          <Field name="party" label={t("bankAccount.owner")} />
          <Field name="holder_name" label={t("bankAccount.holder")} />
          <Field name="number_kind" />
          <Field name="bank" />
          <Field name="currency" />
          <Field name="is_archived" />
        </Group>
      </Form>
    </ResourceList>
  );
}

export function AddressesPage(): React.ReactElement {
  const t = usePartiesT();
  return (
    <ResourceList resource="parties.Address" placement="inline" routed>
      <List resource="parties.Address">
        <Column field="party" />
        <Column field="street" />
        <Column field="city" />
        <Column field="country" />
      </List>
      <Form resource="parties.Address">
        <Field name="street" title />
        <Group label={t("address.details")} columns={2}>
          <Field name="party" />
          <Field name="label" />
          <Field name="city" />
          <Field name="postal_code" />
          <Field name="region" />
          <Field name="country" />
          <Field name="extended" />
          <Field name="po_box" />
          <Field name="is_primary" label={t("address.primaryBilling")} />
        </Group>
      </Form>
    </ResourceList>
  );
}
