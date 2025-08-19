frappe.ui.form.on('Workflow Step Action', {
    refresh: function(frm) {
        if (frm.doc.action_type === 'Approval' || frm.doc.action_type === 'Rejection') {
            frm.set_df_property('next_step', 'hidden', 1);
            frm.set_df_property('next_step', 'reqd', 0);
        } else {
            frm.set_df_property('next_step', 'hidden', 0);
            frm.set_df_property('next_step', 'reqd', 1);
        }
    },
    
    action_type: function(frm) {
        if (frm.doc.action_type === 'Approval' || frm.doc.action_type === 'Rejection') {
            frm.set_value('next_step', '');
            frm.set_df_property('next_step', 'hidden', 1);
            frm.set_df_property('next_step', 'reqd', 0);
        } else {
            frm.set_df_property('next_step', 'hidden', 0);
            frm.set_df_property('next_step', 'reqd', 1);
        }
    }
});