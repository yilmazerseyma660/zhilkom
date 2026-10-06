document.addEventListener('DOMContentLoaded', function () {

    // кнопка меню на телефоне
    var menuBtn = document.getElementById('menuBtn');
    var menuList = document.getElementById('menuList');
    if (menuBtn && menuList) {
        menuBtn.addEventListener('click', function () {
            menuList.classList.toggle('open');
        });
    }

    // слайдер на главной (в версии для слабовидящих не листаем)
    var slider = document.getElementById('slider');
    if (slider && !document.body.classList.contains('vision')) {
        var slides = slider.querySelectorAll('.slide');
        var dots = slider.querySelectorAll('.slider-dots button');
        var current = 0;
        var timer;

        function showSlide(n) {
            slides[current].classList.remove('active');
            dots[current].classList.remove('active');
            current = n;
            slides[current].classList.add('active');
            dots[current].classList.add('active');
        }

        function startTimer() {
            clearInterval(timer);
            timer = setInterval(function () {
                showSlide((current + 1) % slides.length);
            }, 7000);
        }

        dots.forEach(function (dot, i) {
            dot.addEventListener('click', function () {
                showSlide(i);
                startTimer();
            });
        });

        if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            startTimer();
        }
    }

    // подтверждение перед удалением
    document.querySelectorAll('.confirm-delete').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!confirm('Точно удалить? Восстановить будет нельзя.')) {
                e.preventDefault();
            }
        });
    });
});
