const slide = document.getElementById('slide');


function autoScroll() {
    const itemWidth = slide.querySelector('img').offSetWidth + 10;

    //Jump back to the start if at the end
    if (slide.scrollLeft + slide.OffsetWidth >= slide.scrollWidth) {
        
        slide.scrollTo({left: 0, behavior: 'smooth'});
    }
    
    //Otherwise, scroll forward by one image
    else {
        slide.scrollBy({left: itemWidth, behavior: 'smooth'});
    }
}
    //Set how often this function runs
    let slideTime = setInterval(autoScroll, 3000);



