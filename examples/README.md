# GhostSchema examples

Two sample specs to try the tool on. Both are fixtures: small enough to read in full, large enough that slicing visibly saves tokens.

## petstore-openapi.json

A mid-size OpenAPI 3.0 document for a fictional pet store API. It is deliberately planted with things a slicer should drop:

- An unrelated orders surface (`listOrders`, `createOrder`, `getOrder`, and the `Order` schema family).
- Waste schemas referenced by nothing: `LegacyPet`, `AuditRecord`, `Invoice`.
- An external reference: `Order.total` points at `https://example.com/schemas/money.json`. GhostSchema never fetches it. Slice the orders surface and watch it land in the manifest's unresolved list instead:

```bash
ghostschema inspect examples/petstore-openapi.json
ghostschema slice examples/petstore-openapi.json --select getPet -o /tmp/pet-bundle
ghostschema slice examples/petstore-openapi.json --select Order -o /tmp/order-bundle
```

The `getPet` bundle keeps the chain `Pet` to `PetDetails` to `Tag`, plus `PetStatus`, the shared `NotFound` response and `Error` schema, and the `PetId` path parameter, and drops the orders surface by name in the manifest. The `Order` bundle keeps the remote money reference visible in the reduced spec and lists it as unresolved in `manifest.json`.

## schema.graphql

A GraphQL SDL schema for the same fictional store. SDL gets the outline treatment only: no reduced `.graphql` file is ever emitted.

```bash
ghostschema slice examples/schema.graphql --select Pet -o /tmp/pet-outline
```

The bundle holds `outline.json` and `OUTLINE.md`, both labelled outline, listing `Pet`, `PetDetails`, `Tag`, and `PetStatus` with their fields. The manifest (`treatment: outline`) names the dropped types, including the planted waste type `AuditLog`, which nothing references.
