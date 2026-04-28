# Yokedo — Pull Request Checklist

## Architecture

- [ ] Ownership rules respected (no cross-service writes)
- [ ] No cross-service ORM imports

## Database

- [ ] Schema change? → migration created & reviewed
- [ ] DB defaults correctly defined (UUID, timestamps)

## Contracts

- [ ] Headers / auth contract unchanged
- [ ] API conventions respected

## Documentation

- [ ] Data schema updated (if needed)
- [ ] ADR added/updated (if needed)

## Notes
Explain any unchecked item.