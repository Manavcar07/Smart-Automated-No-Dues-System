const body = document.body;

const menuToggle =
document.querySelector(".student-menu-toggle");

const sidebarClose =
document.querySelector(".student-sidebar-close");

const overlay =
document.querySelector(".student-overlay");

function setSidebar(open){

    body.classList.toggle(
        "student-sidebar-open",
        open
    );

}

if(menuToggle){

    menuToggle.addEventListener(
        "click",
        function(){

            setSidebar(true);

        }
    );

}

if(sidebarClose){

    sidebarClose.addEventListener(
        "click",
        function(){

            setSidebar(false);

        }
    );

}

if(overlay){

    overlay.addEventListener(
        "click",
        function(){

            setSidebar(false);

        }
    );

}