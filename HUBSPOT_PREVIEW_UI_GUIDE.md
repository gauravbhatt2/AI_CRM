# HubSpot Preview Modal - UI Layout Guide

## Modal Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Preview for HubSpot Sync                                              ✕   │
│  Review and edit the data below before syncing to HubSpot...                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 KEY METRICS                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Budget          │ Intent         │ Deal Score    │ Industry         │  │
│  │ [____________]  │ [___________]  │ [__________]  │ [_______________]│  │
│  │ Risk Level      │ Product        │               │                  │  │
│  │ [____________]  │ [___________]  │               │                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  🏢 COMPANY & PROCUREMENT                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Mentioned Company    │ Procurement Stage  │ Use Case               │  │
│  │ [________________]   │ [________________] │ [___________________]  │  │
│  │ Budget Owner         │ Implementation Scope  │ Timeline             │  │
│  │ [________________]   │ [_______________]     │ [_________________] │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  💡 STRATEGIC INFORMATION                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ AI Summary                                                         │  │
│  │ ┌────────────────────────────────────────────────────────────────┐ │  │
│  │ │ [                                                            ] │ │  │
│  │ │ [                                                            ] │ │  │
│  │ └────────────────────────────────────────────────────────────────┘ │  │
│  │ Next Action                                                        │  │
│  │ ┌────────────────────────────────────────────────────────────────┐ │  │
│  │ │ [                                                            ] │ │  │
│  │ └────────────────────────────────────────────────────────────────┘ │  │
│  │ Pain Points                                                        │  │
│  │ ┌────────────────────────────────────────────────────────────────┐ │  │
│  │ │ [                                                            ] │ │  │
│  │ │ [                                                            ] │ │  │
│  │ └────────────────────────────────────────────────────────────────┘ │  │
│  │ Decision Criteria                                                  │  │
│  │ ┌────────────────────────────────────────────────────────────────┐ │  │
│  │ │ [                                                            ] │ │  │
│  │ │ [                                                            ] │ │  │
│  │ └────────────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  🔗 CRM LINKS                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Account ID: 12345      │ Contact ID: 67890    │ Deal ID: 24680     │  │
│  │ (Display only)         │ (Display only)       │ (Display only)     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  🏷️  TAGS & RELATIONSHIPS                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Tags                                                                │  │
│  │ [enterprise] [sales] [high-priority]                              │  │
│  │ Stakeholders                                                        │  │
│  │ [John Smith] [Sarah Johnson] [Mike Davis]                         │  │
│  │ Competitors                                                         │  │
│  │ [Competitor A] [Competitor B]                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                        [Cancel]  [✓ Confirm & Sync to HubSpot]│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Section Breakdown

### 1. Modal Header
- Title: "Preview for HubSpot Sync"
- Subtitle: "Review and edit the data below before syncing to HubSpot..."
- Close button (✕) in top-right corner

### 2. Key Metrics Section
**Editable Fields:**
- Budget (text input)
- Intent (text input)
- Deal Score (number input)
- Industry (text input)
- Risk Level (text input)
- Product (text input)

**Layout**: 2-3 column responsive grid

### 3. Company & Procurement Section
**Editable Fields:**
- Mentioned Company (text input)
- Procurement Stage (text input)
- Use Case (text input)
- Budget Owner (text input)
- Implementation Scope (text input)
- Timeline (text input)

**Layout**: 2-3 column responsive grid

### 4. Strategic Information Section
**Editable Fields (Larger textarea):**
- AI Summary (textarea, ~3 rows)
- Next Action (textarea, ~2 rows)
- Pain Points (textarea, ~3 rows)
- Decision Criteria (textarea, ~3 rows)

**Layout**: Full width stacked layout

### 5. CRM Links Section
**Display-Only Fields:**
- Account ID (shown as static value)
- Contact ID (shown as static value)
- Deal ID (shown as static value)

**Layout**: 3 column grid

### 6. Tags & Relationships Section
**Display-Only Content:**
- Tags (pill-style badges in brand color)
- Stakeholders (pill-style badges in blue)
- Competitors (pill-style badges in orange)

**Layout**: Flex wrap badges

### Modal Footer
- Cancel button (gray, left-aligned)
- Confirm & Sync to HubSpot button (gradient blue/purple, right-aligned)

## Visual Features

### Colors & Styling
- **Background**: White (#ffffff)
- **Borders**: Light gray (#e2e8f0)
- **Text**: Dark blue-gray (#0f172a)
- **Labels**: Muted gray (#64748b)
- **Buttons**: Gradient (purple → blue)
- **Input Focus**: Brand blue with soft background

### Animations
- Modal appears with slide-up animation (0.3s)
- Smooth transitions on focus/hover (0.2s)
- Button scale effect on hover

### Responsive Behavior
**Desktop (1200px+)**
- Grid: 3 columns for key metrics & company
- Modal width: max 900px

**Tablet (768px - 1199px)**
- Grid: 2 columns
- Modal width: 80vw

**Mobile (< 768px)**
- Grid: 1 column (full width form)
- Modal padding: reduced
- Stacked buttons in footer

## User Interaction Flow

1. **Initial State**: Modal opens with all fields populated
2. **Editing**: User clicks any input/textarea to edit
3. **Validation**: Text accepts any input (no real-time validation)
4. **Cancel**: Clicking cancel closes modal, discards changes
5. **Confirm**: Clicking confirm shows spinner, syncs with edits
6. **Success**: Modal auto-closes, success message appears below button
7. **Error**: Error message displays, user can retry or cancel

## Accessibility Features

- **Focus Management**: Proper tab order through form fields
- **ARIA Labels**: All inputs have associated labels
- **Semantic HTML**: Proper use of form elements
- **Color Contrast**: WCAG AA compliant
- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: All sections and fields announced properly

## Data Flow Example

```
User clicks "Sync to HubSpot"
         ↓
openHubspotPreview() called
         ↓
buildHubspotPreviewData() creates snapshot
         ↓
Modal opens with populated fields
         ↓
User edits fields
         ↓
Changes stored in hsPreviewEdits state
         ↓
User clicks "Confirm & Sync to HubSpot"
         ↓
pushToHubspot() called with edits
         ↓
API request sent (edits not used in current implementation)
         ↓
Success/Error response received
         ↓
Modal closes, notification shows
```

## Notes

- The current implementation does not apply edits to the API request (for future enhancement)
- Display-only fields help users understand what data is being linked
- All field labels are uppercase for clear visual hierarchy
- Section titles use emoji for quick visual scanning
- The modal is scrollable if content exceeds viewport height
