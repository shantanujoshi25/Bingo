# Bingo Card View (Mobile Screen View)

## Feature Description
This document describes the display and interaction with the user's Bingo card(s) during an active game on a mobile device. The bingo card features a 3x3 grid.

## Visual Elements
*   **Bingo Card Grid:**
    *   Clear, legible display of numbers in a 3x3 grid format.
    *   There is an overlay feature for marked numbers.
    *   Users can highlight numbers in 'amethyst', with the original highlight color being 'gold'.
*   **Marked Numbers:**
    *   Numbers that have been called should be clearly marked/daubed on the card, with an overlay indicating selection.
    *   Different visual states for manually marked vs. auto-marked numbers (if auto-daub is a feature).
*   **Game Information Overlay:**
    *   Small display of game ID, time remaining, current prize.

## User Interaction
*   Users can manually tap to mark numbers on their card as they are called.
*   Visual feedback when a number is successfully marked, with user-specific highlight colors.

## Mobile Considerations
*   Card must be large enough for easy tapping/marking of individual numbers.
*   Clear contrast between marked and unmarked numbers, and between different highlight states.
*   Performance optimization to ensure smooth updates as numbers are called.
