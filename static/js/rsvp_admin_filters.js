(() => {
    'use strict';

    function normalizeNames(value) {
        return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
            .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
    }

    document.querySelectorAll('[data-filter-scope]').forEach(scope => {
        const controls = scope.querySelector('[data-filter-controls]');
        const groups = Array.from(scope.querySelectorAll('[data-filter-group]')).map(element => ({
            element,
            names: normalizeNames(element.dataset.searchNames),
            responses: element.matches('[data-response-row]')
                ? [element] : Array.from(element.querySelectorAll('[data-response-row]'))
        }));
        const fields = Object.fromEntries(
            Array.from(controls.querySelectorAll('[data-filter-field]'))
                .map(field => [field.dataset.filterField, field])
        );
        const count = scope.querySelector('[data-filter-count]');
        const empty = scope.querySelector('[data-filter-empty]');

        function applyFilters() {
            const search = normalizeNames(fields.search.value).split(' ').filter(Boolean);
            const status = fields.status ? fields.status.value : '';
            const attending = fields.attending.value;
            const welcomeParty = fields.welcome_party.value;
            let visible = 0;

            groups.forEach(group => {
                // Keep a household's rowspans intact and apply both answer filters to one RSVP.
                const matchesAnswers = (!attending && !welcomeParty) || group.responses.some(row =>
                    (!attending || row.dataset.attending === attending) &&
                    (!welcomeParty || row.dataset.welcomeParty === welcomeParty)
                );
                const matches = search.every(term => group.names.includes(term)) &&
                    (!status || group.element.dataset.status === status) && matchesAnswers;
                group.element.hidden = !matches;
                if (matches) {
                    visible += 1;
                }
            });

            count.textContent = `Showing ${visible} of ${groups.length} ${scope.dataset.filterUnit}`;
            count.hidden = false;
            empty.hidden = visible !== 0 || groups.length === 0;
        }

        controls.addEventListener('submit', event => event.preventDefault());
        controls.addEventListener('input', applyFilters);
        controls.addEventListener('change', applyFilters);
        controls.querySelector('[data-filter-clear]').addEventListener('click', () => {
            controls.reset();
            applyFilters();
        });
        controls.hidden = false;
        applyFilters();
    });
})();
