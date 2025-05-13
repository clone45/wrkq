# Battle Plan: Adding Task Sidebar

**Date:** May 4, 2025
**Author:** AI Assistant

## Problem Statement

The application currently lacks a sidebar for displaying tasks. We need to implement a sidebar component that will be docked to the left side of the main application window and will initially be open with dummy data. This will serve as a foundation for future task management functionality.

## Approach Overview

We'll leverage Textual's docking and layer system to create an overlay sidebar panel. The sidebar will be docked to the left edge of the application and will be configured to appear above the main content using appropriate CSS layer configuration. The initial implementation will:

1. Create a new widget for the task sidebar
2. Configure it properly with CSS for visual styling and positioning
3. Integrate it into the application's main UI structure
4. Display dummy task data for demonstration purposes
5. Ensure it starts in the "open" state by default

We'll follow Textual's patterns for overlay panels as described in the sidebars_in_textual.md document.

## Implementation Steps

1. **Create TaskSidebar Widget**
   - Create a new file `/job_tracker/ui/widgets/task_sidebar.py`
   - Implement a `TaskSidebar` class that extends `textual.widgets.Static`
   - Include dummy task data for initial display
   - Implement basic styling with `DEFAULT_CSS` for the component

2. **Create CSS for TaskSidebar**
   - Create `/job_tracker/ui/css/task_sidebar.tcss`
   - Define styling that includes:
     - Docking to the left
     - Appropriate width (30-40 cells)
     - Background color and borders
     - Layer configuration for overlay display
     - Default offset of 0 (visible by default)
     - Transition animation for smooth sliding

3. **Modify Main App**
   - Update `/job_tracker/ui/app.py` to:
     - Import the new `TaskSidebar` widget
     - Add it to the app's compose method
     - Configure the app's CSS to support overlay layers
     - Add a key binding for toggling the sidebar visibility (e.g., `t` for tasks)
     - Implement the toggle action method

4. **Update Main CSS**
   - Modify `/job_tracker/ui/css/main.tcss` to include:
     - Layer configuration for the Screen to support base and overlay layers
     - Any necessary adjustments to existing layout to accommodate the sidebar

5. **Add Toggle Functionality**
   - Implement a method in the app to toggle the sidebar visibility
   - Use the offset approach described in the guide to smoothly animate the panel in/out
   - Ensure the sidebar starts in the visible state by default

## Potential Challenges and Solutions

1. **Z-index and Layer Conflicts**
   - Challenge: The sidebar may not appear on top of other content due to layer configuration issues
   - Solution: Ensure proper layer configuration in both the app's CSS and the widget's CSS; verify the yield order in the compose method

2. **Styling and Responsiveness**
   - Challenge: The sidebar may not look consistent across different terminal sizes
   - Solution: Use relative sizing where appropriate and test with various terminal dimensions

3. **Animation Performance**
   - Challenge: The animation might not be smooth on all systems
   - Solution: Keep animations simple and ensure they're properly configured with appropriate easing and duration

4. **Integration with Existing UI**
   - Challenge: The sidebar might disrupt existing layout and UI components
   - Solution: Ensure the sidebar is properly layered as an overlay so it doesn't affect the base layout

5. **Key Binding Conflicts**
   - Challenge: The keyboard shortcut for toggling the sidebar might conflict with existing bindings
   - Solution: Review existing key bindings and choose one that's not already in use