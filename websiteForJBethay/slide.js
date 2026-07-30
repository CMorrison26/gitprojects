(function () {
    const container = document.querySelector('.scroll-container');
    const wrappers = Array.from(document.querySelectorAll('.scroll-track .image-wrapper'));

    if (!container || wrappers.length === 0) return;

    let currentIndex = 0;

    function scrollToIndex(index) {
        if (index === 0) {
            container.scrollTo({ left: 0, behavior: 'smooth' });
        } else {
            const left = wrappers[index].getBoundingClientRect().left
                - container.getBoundingClientRect().left
                + container.scrollLeft;
            container.scrollTo({ left, behavior: 'smooth' });
        }
    }

    setInterval(function () {
        currentIndex = (currentIndex + 1) % wrappers.length;
        scrollToIndex(currentIndex);
    }, 5000);
}());
