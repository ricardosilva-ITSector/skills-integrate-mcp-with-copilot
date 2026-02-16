document.addEventListener("DOMContentLoaded", () => {
  const createForm = document.getElementById("create-activity-form");
  const createMessage = document.getElementById("create-message");
  const adminActivitiesList = document.getElementById("admin-activities-list");

  // Function to show messages
  function showMessage(element, message, type) {
    element.textContent = message;
    element.className = type;
    element.classList.remove("hidden");

    setTimeout(() => {
      element.classList.add("hidden");
    }, 5000);
  }

  // Function to fetch and display activities for admin
  async function fetchActivitiesForAdmin() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      adminActivitiesList.innerHTML = "";

      if (Object.keys(activities).length === 0) {
        adminActivitiesList.innerHTML = "<p>No activities found. Create one above!</p>";
        return;
      }

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "admin-activity-card";

        const spotsLeft = details.max_participants - details.participants.length;
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants (${details.participants.length}):</h5>
              <ul class="participants-list">
                ${details.participants.map((email) => `<li>${email}</li>`).join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <div class="activity-header">
            <h4>${name}</h4>
            <div class="activity-actions">
              <button class="btn-edit" data-activity="${name}">Edit</button>
              <button class="btn-delete" data-activity="${name}">Delete</button>
            </div>
          </div>
          <div class="activity-details">
            <p><strong>Description:</strong> ${details.description}</p>
            <p><strong>Schedule:</strong> ${details.schedule}</p>
            <p><strong>Max Participants:</strong> ${details.max_participants}</p>
            <p><strong>Current Enrollment:</strong> ${details.participants.length} / ${details.max_participants}</p>
            <p><strong>Spots Available:</strong> ${spotsLeft}</p>
          </div>
          ${participantsHTML}
          <div id="edit-form-${name}" class="edit-form hidden">
            <h5>Edit Activity</h5>
            <form class="admin-form">
              <div class="form-group">
                <label>Description:</label>
                <textarea class="edit-description" rows="3">${details.description}</textarea>
              </div>
              <div class="form-group">
                <label>Schedule:</label>
                <input type="text" class="edit-schedule" value="${details.schedule}" />
              </div>
              <div class="form-group">
                <label>Max Participants:</label>
                <input type="number" class="edit-max" value="${details.max_participants}" min="1" />
              </div>
              <div class="form-actions">
                <button type="submit" class="btn-primary">Save Changes</button>
                <button type="button" class="btn-cancel">Cancel</button>
              </div>
            </form>
            <div class="edit-message hidden"></div>
          </div>
        `;

        adminActivitiesList.appendChild(activityCard);

        // Add event listeners
        const editBtn = activityCard.querySelector(".btn-edit");
        const deleteBtn = activityCard.querySelector(".btn-delete");
        const editForm = activityCard.querySelector(`#edit-form-${name} form`);
        const cancelBtn = activityCard.querySelector(".btn-cancel");

        editBtn.addEventListener("click", () => toggleEditForm(name));
        deleteBtn.addEventListener("click", () => deleteActivity(name));
        editForm.addEventListener("submit", (e) => handleEditSubmit(e, name));
        cancelBtn.addEventListener("click", () => toggleEditForm(name));
      });
    } catch (error) {
      adminActivitiesList.innerHTML =
        "<p class='error'>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Toggle edit form visibility
  function toggleEditForm(activityName) {
    const editForm = document.getElementById(`edit-form-${activityName}`);
    editForm.classList.toggle("hidden");
  }

  // Handle create activity form submission
  createForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const name = document.getElementById("new-activity-name").value;
    const description = document.getElementById("new-activity-description").value;
    const schedule = document.getElementById("new-activity-schedule").value;
    const max_participants = parseInt(document.getElementById("new-activity-max").value);

    try {
      const response = await fetch("/admin/activities", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          description,
          schedule,
          max_participants,
        }),
      });

      const result = await response.json();

      if (response.ok) {
        showMessage(createMessage, result.message, "success");
        createForm.reset();
        fetchActivitiesForAdmin();
      } else {
        showMessage(createMessage, result.detail || "Failed to create activity", "error");
      }
    } catch (error) {
      showMessage(createMessage, "Failed to create activity. Please try again.", "error");
      console.error("Error creating activity:", error);
    }
  });

  // Handle edit activity
  async function handleEditSubmit(event, activityName) {
    event.preventDefault();

    const form = event.target;
    const description = form.querySelector(".edit-description").value;
    const schedule = form.querySelector(".edit-schedule").value;
    const max_participants = parseInt(form.querySelector(".edit-max").value);

    const messageDiv = form.parentElement.querySelector(".edit-message");

    try {
      const response = await fetch(`/admin/activities/${encodeURIComponent(activityName)}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description,
          schedule,
          max_participants,
        }),
      });

      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        toggleEditForm(activityName);
        fetchActivitiesForAdmin();
      } else {
        showMessage(messageDiv, result.detail || "Failed to update activity", "error");
      }
    } catch (error) {
      showMessage(messageDiv, "Failed to update activity. Please try again.", "error");
      console.error("Error updating activity:", error);
    }
  }

  // Handle delete activity
  async function deleteActivity(activityName) {
    if (!confirm(`Are you sure you want to delete "${activityName}"? This will also remove all enrolled students.`)) {
      return;
    }

    try {
      const response = await fetch(`/admin/activities/${encodeURIComponent(activityName)}`, {
        method: "DELETE",
      });

      const result = await response.json();

      if (response.ok) {
        alert(result.message);
        fetchActivitiesForAdmin();
      } else {
        alert(result.detail || "Failed to delete activity");
      }
    } catch (error) {
      alert("Failed to delete activity. Please try again.");
      console.error("Error deleting activity:", error);
    }
  }

  // Initialize admin dashboard
  fetchActivitiesForAdmin();
});
