/**
 * TablePaginator - Lightweight, dependency-free vanilla JS paginator
 * for Cartivo Superadmin Tables with native print support.
 */
class TablePaginator {
    constructor(options) {
        this.tableBody = document.getElementById(options.tableBodyId);
        this.rowSelector = options.rowSelector;
        this.rows = Array.from(document.querySelectorAll(options.rowSelector));
        this.infoEl = document.getElementById(options.infoId);
        this.paginationEl = document.getElementById(options.paginationId);
        this.pageSizeSelect = document.getElementById(options.pageSizeSelectId);
        this.searchInput = document.getElementById(options.searchInputId);
        this.emptyStateEl = document.getElementById(options.emptyStateId);
        this.printBtn = document.getElementById(options.printBtnId);
        this.itemName = options.itemName || 'entries';
        this.customFilter = options.customFilter || null;

        this.currentPage = 1;
        this.pageSize = options.defaultPageSize || 5;
        this.filteredRows = [...this.rows];

        this.init();
    }

    init() {
        if (!this.rows.length) return;

        // Page size dropdown listener
        if (this.pageSizeSelect) {
            this.pageSizeSelect.value = String(this.pageSize);
            this.pageSizeSelect.addEventListener('change', (e) => {
                const val = e.target.value;
                this.pageSize = val === 'all' ? this.filteredRows.length : parseInt(val, 10);
                this.currentPage = 1;
                this.render();
            });
        }

        // Live search listener
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => {
                this.applyFilter();
            });
        }

        // Print button trigger
        if (this.printBtn) {
            this.printBtn.addEventListener('click', () => {
                window.print();
            });
        }

        // Browser Print hooks to show all matching rows during print
        window.addEventListener('beforeprint', () => {
            this.filteredRows.forEach(row => {
                row.style.display = '';
            });
        });

        window.addEventListener('afterprint', () => {
            this.render();
        });

        this.applyFilter();
    }

    setCustomFilter(fn) {
        this.customFilter = fn;
        this.applyFilter();
    }

    applyFilter() {
        const query = (this.searchInput?.value || '').toLowerCase().trim();

        this.filteredRows = this.rows.filter(row => {
            // Search text match
            let matchesSearch = true;
            if (query) {
                const text = row.textContent.toLowerCase();
                matchesSearch = text.includes(query);
            }

            // Custom category or metadata filter
            let matchesCustom = true;
            if (this.customFilter) {
                matchesCustom = this.customFilter(row);
            }

            return matchesSearch && matchesCustom;
        });

        this.currentPage = 1;
        this.render();
    }

    render() {
        const total = this.filteredRows.length;
        const effectivePageSize = (this.pageSize === 'all' || this.pageSize >= total) ? (total || 1) : this.pageSize;
        const totalPages = Math.max(1, Math.ceil(total / effectivePageSize));

        if (this.currentPage > totalPages) {
            this.currentPage = totalPages;
        }

        const startIndex = (this.currentPage - 1) * effectivePageSize;
        const endIndex = Math.min(startIndex + effectivePageSize, total);

        // Hide all rows first
        this.rows.forEach(row => {
            row.style.display = 'none';
        });

        // Show slice of filtered rows
        for (let i = startIndex; i < endIndex; i++) {
            if (this.filteredRows[i]) {
                this.filteredRows[i].style.display = '';
            }
        }

        // Empty state toggle
        if (this.emptyStateEl) {
            this.emptyStateEl.style.display = total === 0 ? 'block' : 'none';
        }

        // Update info container ("Showing 1 to 5 of 20 entries")
        if (this.infoEl) {
            if (total === 0) {
                this.infoEl.innerHTML = `Showing <span class="font-bold text-white">0</span> to <span class="font-bold text-white">0</span> of <span class="font-bold text-white">0</span> ${this.itemName}`;
            } else {
                this.infoEl.innerHTML = `Showing <span class="font-bold text-white">${startIndex + 1}</span> to <span class="font-bold text-white">${endIndex}</span> of <span class="font-bold text-white">${total}</span> ${this.itemName}`;
            }
        }

        // Render pagination buttons
        this.renderControls(totalPages);

        // Re-trigger Lucide icon scan if any icons exist in controls
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    renderControls(totalPages) {
        if (!this.paginationEl) return;
        this.paginationEl.innerHTML = '';

        if (totalPages <= 1 && this.filteredRows.length <= this.pageSize) {
            this.paginationEl.style.display = 'none';
            return;
        }
        this.paginationEl.style.display = 'flex';

        // Prev Button
        const prevBtn = document.createElement('button');
        prevBtn.type = 'button';
        prevBtn.disabled = this.currentPage === 1;
        prevBtn.className = `flex items-center justify-center w-8 h-8 rounded-xl text-xs font-semibold border transition-all ${
            this.currentPage === 1 
                ? 'bg-slate-800/40 text-slate-600 border-slate-800 cursor-not-allowed' 
                : 'bg-[#0f172a] text-slate-300 hover:text-white hover:bg-slate-800 border-[#1e293b] cursor-pointer'
        }`;
        prevBtn.innerHTML = `<i data-lucide="chevron-left" class="w-3.5 h-3.5"></i>`;
        prevBtn.title = 'Previous Page';
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.render();
            }
        });
        this.paginationEl.appendChild(prevBtn);

        // Calculate visible page range (up to 5 pages window)
        let startPage = Math.max(1, this.currentPage - 2);
        let endPage = Math.min(totalPages, startPage + 4);
        if (endPage - startPage < 4) {
            startPage = Math.max(1, endPage - 4);
        }

        if (startPage > 1) {
            this.addPageBtn(1);
            if (startPage > 2) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'w-6 text-center text-slate-500 text-xs self-center';
                ellipsis.textContent = '...';
                this.paginationEl.appendChild(ellipsis);
            }
        }

        for (let p = startPage; p <= endPage; p++) {
            this.addPageBtn(p);
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'w-6 text-center text-slate-500 text-xs self-center';
                ellipsis.textContent = '...';
                this.paginationEl.appendChild(ellipsis);
            }
            this.addPageBtn(totalPages);
        }

        // Next Button
        const nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.disabled = this.currentPage === totalPages;
        nextBtn.className = `flex items-center justify-center w-8 h-8 rounded-xl text-xs font-semibold border transition-all ${
            this.currentPage === totalPages 
                ? 'bg-slate-800/40 text-slate-600 border-slate-800 cursor-not-allowed' 
                : 'bg-[#0f172a] text-slate-300 hover:text-white hover:bg-slate-800 border-[#1e293b] cursor-pointer'
        }`;
        nextBtn.innerHTML = `<i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>`;
        nextBtn.title = 'Next Page';
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.render();
            }
        });
        this.paginationEl.appendChild(nextBtn);
    }

    addPageBtn(pageNum) {
        const btn = document.createElement('button');
        btn.type = 'button';
        const isActive = pageNum === this.currentPage;
        btn.className = `w-8 h-8 rounded-xl text-xs font-bold transition-all ${
            isActive 
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30' 
                : 'bg-[#0f172a] text-slate-400 hover:text-white hover:bg-slate-800 border border-[#1e293b] cursor-pointer'
        }`;
        btn.textContent = pageNum;
        btn.addEventListener('click', () => {
            this.currentPage = pageNum;
            this.render();
        });
        this.paginationEl.appendChild(btn);
    }
}

window.TablePaginator = TablePaginator;
