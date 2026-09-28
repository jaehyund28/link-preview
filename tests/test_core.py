import unittest

from link_cut_tree import LinkCutForest


class TestMakeNode(unittest.TestCase):
    def test_default_value_is_zero(self):
        f = LinkCutForest()
        n = f.make_node()
        self.assertEqual(f.get_value(n), 0)

    def test_assigned_ids_are_sequential(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        c = f.make_node(3)
        self.assertEqual([a, b, c], [0, 1, 2])

    def test_set_value_updates_get_value(self):
        f = LinkCutForest()
        n = f.make_node(5)
        f.set_value(n, 42)
        self.assertEqual(f.get_value(n), 42)


class TestLinkCut(unittest.TestCase):
    def test_isolated_node_is_its_own_root(self):
        f = LinkCutForest()
        n = f.make_node()
        self.assertEqual(f.find_root(n), n)

    def test_link_sets_parent(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        f.link(b, a)
        self.assertEqual(f.find_root(b), a)

    def test_link_chain_of_three(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        c = f.make_node()
        f.link(b, a)
        f.link(c, b)
        self.assertEqual(f.find_root(c), a)

    def test_link_self_raises(self):
        f = LinkCutForest()
        a = f.make_node()
        with self.assertRaises(ValueError):
            f.link(a, a)

    def test_link_non_root_child_raises(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        c = f.make_node()
        f.link(b, a)
        f.link(c, b)
        # c is not a root; linking it again should fail
        with self.assertRaises(ValueError):
            f.link(c, a)

    def test_link_cycle_raises(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        f.link(b, a)
        # a and b are in the same tree; linking a under b would cycle
        with self.assertRaises(ValueError):
            f.link(a, b)

    def test_cut_detaches_child(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        f.link(b, a)
        f.cut(b)
        self.assertEqual(f.find_root(b), b)
        self.assertEqual(f.find_root(a), a)

    def test_cut_root_raises(self):
        f = LinkCutForest()
        a = f.make_node()
        with self.assertRaises(ValueError):
            f.cut(a)

    def test_cut_middle_of_chain(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        c = f.make_node()
        f.link(b, a)
        f.link(c, b)
        f.cut(b)
        self.assertEqual(f.find_root(c), b)
        self.assertEqual(f.find_root(a), a)


class TestConnected(unittest.TestCase):
    def test_isolated_nodes_not_connected(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        self.assertFalse(f.connected(a, b))

    def test_same_node_is_connected(self):
        f = LinkCutForest()
        a = f.make_node()
        self.assertTrue(f.connected(a, a))

    def test_linked_nodes_connected(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        c = f.make_node()
        f.link(b, a)
        f.link(c, b)
        self.assertTrue(f.connected(a, c))
        self.assertTrue(f.connected(b, c))

    def test_cut_disconnects(self):
        f = LinkCutForest()
        a = f.make_node()
        b = f.make_node()
        c = f.make_node()
        f.link(b, a)
        f.link(c, b)
        f.cut(b)
        self.assertFalse(f.connected(a, c))


class TestPathSum(unittest.TestCase):
    def test_single_node_returns_its_value(self):
        f = LinkCutForest()
        a = f.make_node(7)
        self.assertEqual(f.path_sum(a, a), 7)

    def test_two_node_path(self):
        f = LinkCutForest()
        a = f.make_node(3)
        b = f.make_node(4)
        f.link(b, a)
        self.assertEqual(f.path_sum(a, b), 7)

    def test_path_sum_includes_endpoints(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        c = f.make_node(3)
        f.link(b, a)
        f.link(c, b)
        self.assertEqual(f.path_sum(a, c), 6)

    def test_path_sum_after_set_value(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        f.link(b, a)
        f.set_value(b, 10)
        self.assertEqual(f.path_sum(a, b), 11)

    def test_path_sum_disconnected_raises(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        with self.assertRaises(ValueError):
            f.path_sum(a, b)

    def test_path_sum_after_cut(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        c = f.make_node(3)
        f.link(b, a)
        f.link(c, b)
        f.cut(b)
        with self.assertRaises(ValueError):
            f.path_sum(a, c)

    def test_path_sum_symmetric(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        c = f.make_node(3)
        d = f.make_node(4)
        f.link(b, a)
        f.link(c, b)
        f.link(d, c)
        self.assertEqual(f.path_sum(a, d), f.path_sum(d, a))


class TestReRooting(unittest.TestCase):
    def test_link_after_cut(self):
        f = LinkCutForest()
        a = f.make_node(1)
        b = f.make_node(2)
        c = f.make_node(3)
        f.link(b, a)
        f.link(c, b)
        f.cut(b)
        # Now reattach c under a directly
        f.link(c, a)
        self.assertTrue(f.connected(a, c))
        self.assertEqual(f.path_sum(a, c), 4)

    def test_branching_tree(self):
        f = LinkCutForest()
        root = f.make_node(1)
        a = f.make_node(2)
        b = f.make_node(3)
        c = f.make_node(4)
        f.link(a, root)
        f.link(b, root)
        f.link(c, root)
        self.assertEqual(f.path_sum(a, b), 6)
        self.assertEqual(f.path_sum(a, c), 7)
        self.assertEqual(f.path_sum(b, c), 8)

    def test_deep_chain_sum(self):
        f = LinkCutForest()
        ids = [f.make_node(i + 1) for i in range(10)]
        for i in range(1, 10):
            f.link(ids[i], ids[i - 1])
        # sum 1..10 = 55
        self.assertEqual(f.path_sum(ids[0], ids[9]), 55)


if __name__ == "__main__":
    unittest.main()
