frappe.ui.form.on('Workflow Transition', {
    refresh: function(frm) {
        if (frm.doc.auto_transition) {
            frm.set_df_property('transition_action', 'hidden', 1);
            frm.set_df_property('transition_action', 'reqd', 0);
        } else {
            frm.set_df_property('transition_action', 'hidden', 0);
            frm.set_df_property('transition_action', 'reqd', 1);
        }
    },
    
    auto_transition: function(frm) {
        if (frm.doc.auto_transition) {
            frm.set_value('transition_action', '');
            frm.set_df_property('transition_action', 'hidden', 1);
            frm.set_df_property('transition_action', 'reqd', 0);
        } else {
            frm.set_df_property('transition_action', 'hidden', 0);
            frm.set_df_property('transition_action', 'reqd', 1);
        }
    }
});