/**
 * Tailwind CSS, built at image build time (see the Dockerfile's "css" stage, or scripts/build_css.sh locally).
 * Only class names that appear literally in these files end up in app.css, so never build class names from pieces.
 */
module.exports = {
    content: ['./app/templates/**/*.html', './app/static/js/**/*.js'],
    theme: { extend: {} },
    plugins: [],
};
