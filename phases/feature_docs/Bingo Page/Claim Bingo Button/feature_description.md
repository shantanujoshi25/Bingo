# Claim Bingo Button (Mobile Screen View)

## Feature Description
This document describes the "Claim Bingo" button, its visibility, and interaction on the mobile Bingo game screen.

## Visual Elements
*   **Button Appearance:**
    *   A prominent, clearly labeled button: "BINGO!".
    *   Often brightly colored or animated to draw attention when a Bingo is possible.
*   **Visibility State:**
    *   The button should be inactive/greyed out when no Bingo is possible.
    *   It should become active/highlighted when a winning pattern is detected on one or more of the user's cards.
*   **Confirmation Dialog (optional):**
    *   After tapping, a quick confirmation (e.g., "Are you sure you want to claim?") to prevent accidental claims.

## User Interaction
*   Users tap the button to declare a Bingo.
*   The button should only be active when a valid Bingo pattern is present on a card.
*   Upon successful claim, appropriate feedback (e.g., "Bingo Claimed!", sound effect) and transition to a results screen.
*   If the claim is invalid, clear feedback is provided (e.g., "No Bingo!").

## Mobile Considerations
*   Large and easily tappable, usually located at the bottom or a prominent side of the screen.
*   Should not obscure the Bingo card or called numbers.
*   Quick response time for tap events to ensure timely claims.
