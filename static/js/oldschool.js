/**
 * Old School Interactive Line-Item & Calculation Helpers
 */
document.addEventListener("DOMContentLoaded", function () {
  // Format currency helper
  window.formatVND = function (num) {
    const n = Number(num) || 0;
    return n.toLocaleString("vi-VN") + " đ";
  };

  // Recalculate totals on dynamic line tables
  window.recalcLineTable = function (tableId, grandTotalSelector) {
    const table = document.getElementById(tableId);
    if (!table) return;
    let grandTotal = 0;
    table.querySelectorAll("tbody tr.line-item-row").forEach(function (row) {
      const qtyInput = row.querySelector(".line-qty-input");
      const priceInput = row.querySelector(".line-price-input");
      const discInput = row.querySelector(".line-disc-input");
      const totalCell = row.querySelector(".line-total-display");

      const qty = parseFloat(qtyInput ? qtyInput.value : 0) || 0;
      const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
      const disc = parseFloat(discInput ? discInput.value : 0) || 0;
      const lineTotal = Math.max(0, qty * price - disc);
      grandTotal += lineTotal;
      if (totalCell) {
        totalCell.textContent = window.formatVND(lineTotal);
      }
    });
    const gtEl = document.querySelector(grandTotalSelector);
    if (gtEl) {
      gtEl.textContent = window.formatVND(grandTotal);
    }
  };
});
