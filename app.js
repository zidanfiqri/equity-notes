document.addEventListener("DOMContentLoaded", () => {
    // Pastikan nama file ini sama persis dengan yang Anda upload ke repositori GitHub
    const riCsvUrl = 'Equity Notes.xlsx - RI Play.csv';
    const tenderCsvUrl = 'Equity Notes.xlsx - Tender Offer.csv';

    function fetchAndRenderCSV(url, tableHeadersId, tableBodyId) {
        Papa.parse(url, {
            download: true,
            header: true,
            skipEmptyLines: true,
            complete: function(results) {
                const data = results.data;
                if (data.length === 0) return;

                // Render Headers
                const headers = Object.keys(data[0]).filter(header => header.trim() !== "");
                const headerRow = document.getElementById(tableHeadersId);
                headers.forEach(headerText => {
                    const th = document.createElement("th");
                    th.textContent = headerText;
                    headerRow.appendChild(th);
                });

                // Render Body
                const body = document.getElementById(tableBodyId);
                data.forEach(row => {
                    // Skip baris jika Ticker kosong
                    if (!row["Ticker"] || row["Ticker"].trim() === "") return;

                    const tr = document.createElement("tr");
                    headers.forEach(header => {
                        const td = document.createElement("td");
                        let cellValue = row[header] || "-";

                        // Formatting khusus untuk kolom Status
                        if (header === "Status") {
                            const statusLower = cellValue.toLowerCase();
                            if (statusLower.includes("on going")) {
                                cellValue = `<span class="status-ongoing">${cellValue}</span>`;
                            } else if (statusLower.includes("pipeline")) {
                                cellValue = `<span class="status-pipeline">${cellValue}</span>`;
                            } else if (statusLower.includes("postponed")) {
                                cellValue = `<span class="status-postponed">${cellValue}</span>`;
                            }
                            td.innerHTML = cellValue;
                        } 
                        // Formatting khusus untuk kolom Ticker agar menonjol
                        else if (header === "Ticker") {
                            td.innerHTML = `<strong>${cellValue}</strong>`;
                        }
                        // Formatting untuk Sumber/Link Prospektus
                        else if (header === "Sumber" && cellValue !== "-" && cellValue.includes("http")) {
                            td.innerHTML = `<a href="${cellValue}" target="_blank" class="text-decoration-none">🔗 Link</a>`;
                        } else {
                            td.textContent = cellValue;
                        }
                        tr.appendChild(td);
                    });
                    body.appendChild(tr);
                });
            },
            error: function(error) {
                console.error("Error fetching CSV:", error);
                document.getElementById(tableBodyId).innerHTML = `<tr><td colspan="10" class="text-center text-danger">Gagal memuat data dari ${url}. Pastikan nama file CSV benar.</td></tr>`;
            }
        });
    }

    // Eksekusi pengambilan data
    fetchAndRenderCSV(riCsvUrl, "riHeaders", "riBody");
    fetchAndRenderCSV(tenderCsvUrl, "tenderHeaders", "tenderBody");

    // Fitur Live Search
    document.getElementById("searchInput").addEventListener("keyup", function() {
        let filter = this.value.toUpperCase();
        let rows = document.querySelectorAll("tbody tr");

        rows.forEach(row => {
            let ticker = row.cells[0]?.textContent || ""; // Asumsi Ticker ada di kolom pertama
            if (ticker.toUpperCase().indexOf(filter) > -1) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    });
});